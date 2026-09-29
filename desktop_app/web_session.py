"""Headless application assembly for the WebView presentation.

All business gates remain in the existing services. This module does not own Tk.
"""
import copy
import threading
from pathlib import Path
from .config import DEFAULT, data_directory, load_config, InstanceLock
from .core import Store, Engine
from .profiles import Profiles
from .gateways import DemoQueries, OracleQueries, DemoIdentity, CompanyIdentity
from .choices import ChoiceForms
from .conversation_actions import ActionService
from .workflows import WorkflowService
from .outcomes import OutcomeService


class WebSession:
    def __init__(self, directory=None, config=None, config_path=None, groq_trial=False):
        if groq_trial and (config is not None or config_path is not None):
            raise ValueError('試用不能載入公司設定。')
        self.directory=Path(directory or data_directory())
        if groq_trial:self.directory /= 'groq-trial'
        self.trial=groq_trial
        self.config=copy.deepcopy(DEFAULT) if groq_trial else config or load_config(config_path or self.directory/'config.json')
        self.lock=InstanceLock(self.directory)
        self.stop=threading.Event();self.closed=False;self.engine=None
        try:
            self.identity=(DemoIdentity() if self.config['identity_mode']=='demo' else CompanyIdentity()).current()
            self.store=Store(self.directory/'local-v1.sqlite3')
            if groq_trial:
                from .trial import TrialProfiles
                from .report_engine import ReportEngine
                self.profiles=TrialProfiles();engine_class=ReportEngine
            else:
                self.profiles=Profiles(self.directory/'assistants.json',self.config['assistant']);engine_class=Engine
            self.queries=DemoQueries() if self.config['query_mode']=='demo' else OracleQueries()
            self.engine=engine_class(self.store,self.queries.run,None,query_validator=self.queries.validate,
                query_catalog=self.queries.catalog,assistant_router=self.profiles.respond,binding_validator=self.profiles.validate)
            self.actions=ActionService(self.engine);self.workflows=WorkflowService(self.engine,self.profiles)
            self.outcomes=OutcomeService(self.workflows);self.forms=ChoiceForms(self.store.path)
            self.preferences_path=self.directory/'ui-preferences.json'
            from .dialogue_store import DialogueStore
            from .dialogue_service import DialogueService
            self.dialogue=DialogueService(DialogueStore(self.directory/'dialogue-v1.sqlite3'))
            self.scheduler_error=False
            self.scheduler=threading.Thread(target=self._tick,daemon=True);self.scheduler.start()
        except BaseException:
            if self.engine:self.engine.close(wait=True)
            self.lock.close();raise

    def _tick(self):
        while not self.stop.wait(3):
            try:self.engine.tick()
            except Exception:self.scheduler_error=True

    def close(self):
        if self.closed:return
        self.closed=True;self.stop.set();self.scheduler.join()
        try:self.engine.close(wait=True)
        finally:self.lock.close()
