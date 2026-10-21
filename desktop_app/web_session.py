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
    def __init__(self, directory=None, config=None, config_path=None, groq_trial=False, login_session=None, demo_session=None, *, start_scheduler=True, deployment_defaults=None, activation_enabled=True):
        if groq_trial and (config is not None or config_path is not None):
            raise ValueError('試用不能載入連線設定。')
        if demo_session is not None and (config_path is not None or config is None
                or config != DEFAULT or groq_trial or login_session is not None):
            raise ValueError('展示登入不能載入公司或使用者設定。')
        self.directory=Path(directory or data_directory())
        if groq_trial:self.directory /= 'groq-trial'
        self.trial=groq_trial;self.activation_enabled=activation_enabled is True
        self.config=copy.deepcopy(DEFAULT) if groq_trial else config or load_config(config_path or self.directory/'config.json')
        self.demo_session=demo_session
        if demo_session is not None:
            from .demo_login import DemoLoginSession
            if (type(demo_session) is not DemoLoginSession or groq_trial or login_session is not None
                    or self.config != DEFAULT or config_path is not None
                    or self.directory.resolve() != demo_session.directory
                    or any(self.directory.iterdir())):
                raise ValueError('展示登入只能開啟空白暫存工作區及離線預設；禁止公司連線。')
            demo_session.current()
        self.login_session=login_session
        if self.config['identity_mode']=='company':
            self.identity=CompanyIdentity(login_session).current()
            self.directory=login_session.directory(self.directory)
        else:
            if login_session is not None:raise ValueError('登入身分與工作區模式不符。')
            self.identity=demo_session.current() if demo_session else DemoIdentity().current()
        self.lock=InstanceLock(self.directory)
        self.stop=threading.Event();self.closed=False;self.engine=None
        try:
            self.store=Store(self.directory/'local-v1.sqlite3')
            if groq_trial:
                from .trial import TrialProfiles
                from .report_engine import ReportEngine
                self.profiles=TrialProfiles();engine_class=ReportEngine
            else:
                self.profiles=Profiles(self.directory/'assistants.json',self.config['assistant']);engine_class=Engine
            self.queries=DemoQueries() if self.config['query_mode']=='demo' else OracleQueries()
            if self.demo_session:
                self.profiles.authorization=self.demo_session.current
            if self.login_session or self.demo_session:
                from .authentication import AuthorizedQueries
                self.profiles.authorization=(self.login_session or self.demo_session).current
                self.queries=AuthorizedQueries(self.queries,self.login_session or self.demo_session)
            self.engine=engine_class(self.store,self.queries.run,None,query_validator=self.queries.validate,
                query_catalog=self.queries.catalog,assistant_router=self.profiles.respond,binding_validator=self.profiles.validate)
            self.engine.authorization=self.assert_identity
            self.actions=ActionService(self.engine);self.workflows=WorkflowService(self.engine,self.profiles)
            from .skills import SkillService
            self.skills=SkillService(self.engine,self.profiles,self.workflows)
            from .assistant_briefings import AssistantBriefings
            self.briefings=AssistantBriefings(self.engine,self.profiles)
            from .work_orders import WorkOrders
            self.orders=WorkOrders(self.engine,self.profiles,self.briefings)
            self.outcomes=OutcomeService(self.workflows);self.forms=ChoiceForms(self.store.path)
            from .data_cleanup import DataCleanup
            self.cleanup=DataCleanup(self.engine)
            self.preferences_path=self.directory/'ui-preferences.json'
            from .dialogue_store import DialogueStore
            from .dialogue_service import DialogueService
            from .dialogue_provider import ProfileDialogueProvider
            self.dialogue=DialogueService(DialogueStore(self.directory/'dialogue-v1.sqlite3'),ProfileDialogueProvider(self.profiles))
            self.dialogue.authorization=self.assert_identity
            from .company_readiness import CompanyProbe
            self.company_probe=CompanyProbe(self.profiles)
            from .continuity import Continuity
            from .activation import Activation
            self.continuity=Continuity(self);self.skills.continuity=self.continuity
            use_defaults=(config is None) if deployment_defaults is None else deployment_defaults is True
            self.activation=Activation(self,load_defaults=use_defaults and not (groq_trial or demo_session))
            self.scheduler_error=False
            self.scheduler=None
            if start_scheduler:
                self.scheduler=threading.Thread(target=self._tick,daemon=True);self.scheduler.start()
        except BaseException:
            if self.engine:self.engine.close(wait=True)
            self.lock.close();raise

    def assert_identity(self):
        if self.demo_session:self.demo_session.current()
        if self.login_session:self.login_session.current()

    def _tick(self):
        while not self.stop.wait(3):
            try:
                self.assert_identity()
                self.engine.tick()
            except Exception:self.scheduler_error=True

    def close(self):
        if self.closed:return
        self.closed=True;self.stop.set()
        if self.scheduler is not None:self.scheduler.join()
        self.dialogue.close(wait=False)
        self.company_probe.close(wait=False)
        try:
            self.engine.close(wait=True)
            self.engine.wait_closed()
        finally:
            try:self.dialogue.close(wait=True)
            finally:
                try:self.company_probe.close(wait=True)
                finally:
                    self.lock.close()
                    if self.login_session:self.login_session.close()
                    if self.demo_session:self.demo_session.close()
