"""Environment checks exercise malformed inputs without internal services or secrets."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

doctor = module('environment_doctor', 'doctor.py')
bundle = module('environment_bundle', 'offline_bundle.py')
installer = module('environment_installer', 'install-offline.py')
code_zip = module('environment_code_zip', 'code_zip_bundle.py')


class DiagnosticTests(unittest.TestCase):
    def test_share_report_is_whitelisted_and_checks_continue(self):
        secret = 'PRIVATE_ACCOUNT_SECRET_88442'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            config.write_text(json.dumps({'assistant': {'mode':'company', 'base_url':'https://' + secret + '.example/v1',
                'model': secret, 'api_key_env': secret, 'header_env': {'X-Test': secret}, 'ca_bundle':str(root / secret)}}), encoding='utf-8')
            with patch.object(doctor.importlib.metadata, 'distributions', side_effect=RuntimeError(secret)):
                report = doctor.inspect_environment(root, config, root / 'new-data', {secret:secret})
            encoded = json.dumps(report)
            self.assertNotIn(secret, encoded)
            self.assertNotIn(str(root), encoded)
            self.assertEqual(set(report), {'schema_version','local_environment','company_acceptance','python_version','architecture_bits','tk_patch','packages','checks'})
            states = {item['check']: item['status'] for item in report['checks']}
            self.assertEqual(states['dependencies'], 'failed')
            self.assertEqual(states['ca_bundle'], 'failed')
            self.assertEqual(states['credential_presence'], 'passed')
            self.assertEqual(states['data_directory'], 'passed')
            self.assertEqual(states['company_chatbot'], 'not_tested')
            self.assertFalse((root / 'new-data').exists())
            self.assertTrue(all(set(item) == {'check','status','code'} for item in report['checks']))

    def test_invalid_config_does_not_hide_directory_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / 'bad.json'; bad.write_text('broken private text', encoding='utf-8')
            report = doctor.inspect_environment(ROOT, bad, bad, {})
            states = {item['check']:item['status'] for item in report['checks']}
            self.assertEqual(states['configuration'], 'failed')
            self.assertEqual(states['data_directory'], 'failed')
            self.assertEqual(states['company_identity'], 'not_tested')

    def test_company_missing_credentials_and_invalid_endpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = root / 'config.json'
            source = {'assistant':{'mode':'company','base_url':'https://internal.example/v1','model':'test','api_key_env':'TEST_COMPANY_KEY'}}
            config.write_text(json.dumps(source), encoding='utf-8')
            report = doctor.inspect_environment(ROOT, config, root, {})
            self.assertIn({'check':'credential_presence','status':'failed','code':'required_environment_missing_or_invalid'}, report['checks'])
            source['assistant']['base_url'] = 'https://api.openai.com/v1'
            config.write_text(json.dumps(source), encoding='utf-8')
            report = doctor.inspect_environment(ROOT, config, root, {})
            self.assertIn({'check':'configuration','status':'failed','code':'configuration_invalid'}, report['checks'])


    def test_profiles_use_data_directory_and_keyring_without_legacy_key(self):
        from desktop_app.profiles import Profiles, CredentialVault
        secret = 'PRIVATE_PROFILE_SECRET_94012'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); data=root/'data'; config=root/'config.json'
            config.write_text(json.dumps({'assistant':{'mode':'company','base_url':'https://company.example/v1','model':'test','api_key_env':'MISSING_OLD_KEY'}}),encoding='utf-8')
            profiles=Profiles(data/'assistants.json')
            profiles.save(secret,secret,secret)
            profiles.data['credential_source']='keyring'
            profiles._write(profiles.data)
            before=(data/'assistants.json').read_bytes()
            with patch.object(doctor,'data_directory',return_value=data), patch.object(CredentialVault,'get',return_value=secret):
                report=doctor.inspect_environment(ROOT,config,environ={})
            states={v['check']:v['status'] for v in report['checks']}
            self.assertEqual(states['assistant_profiles'],'passed')
            self.assertEqual(states['profile_credential'],'passed')
            self.assertEqual(states['credential_presence'],'passed')
            self.assertEqual(states['company_chatbot'],'not_tested')
            self.assertNotIn(secret,json.dumps(report))
            self.assertEqual(before,(data/'assistants.json').read_bytes())
            with patch.object(doctor,'data_directory',return_value=data), patch.object(CredentialVault,'get',side_effect=RuntimeError(secret)):
                failed=doctor.inspect_environment(ROOT,config,environ={})
            self.assertIn({'check':'profile_credential','status':'failed','code':'credential_store_unavailable_or_empty'},failed['checks'])
            self.assertNotIn(secret,json.dumps(failed))

    def test_adapter_restrictions_fail_before_company_calls(self):
        invalids = [
            {"header_env":{"Authorization":"TEST_KEY"}},
            {"header_env":{"Bad Header":"TEST_KEY"}},
            {"assistant_ref":"helper"},
            {"assistant_ref":"helper", "assistant_ref_field":"messages"},
            {"ca_bundle":""},
            {"base_url":"https://api.openai.com./v1"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'config.json'
            missing = doctor.inspect_environment(ROOT, path, root, {})
            self.assertIn({'check':'configuration','status':'failed','code':'configuration_invalid'}, missing['checks'])
            for invalid in invalids:
                with self.subTest(invalid=invalid):
                    source = {'assistant':{'mode':'company','base_url':'https://company.example/v1','model':'test',**invalid}}
                    path.write_text(json.dumps(source), encoding='utf-8')
                    report = doctor.inspect_environment(ROOT, path, root, {})
                    self.assertIn({'check':'configuration','status':'failed','code':'configuration_invalid'}, report['checks'])
                    self.assertIn({'check':'data_directory','status':'passed','code':'ok'}, report['checks'])
            source = {'assistant':{'mode':'company','base_url':'https://company.example/v1','model':'test','header_env':{'X-Test':'TEST_HEADER'}}}
            path.write_text(json.dumps(source), encoding='utf-8')
            report = doctor.inspect_environment(ROOT, path, root, {'UNITHELPER_API_KEY':'key','TEST_HEADER':'bad\r\nvalue'})
            self.assertIn({'check':'credential_presence','status':'failed','code':'required_environment_missing_or_invalid'}, report['checks'])



class OfflineBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lock = self.root / 'requirements.lock'; self.lock.write_text('sample==1.0\n', encoding='ascii')
        self.folder = self.root / 'wheelhouse'; self.folder.mkdir()
        self.wheel = self.folder / 'sample-1.0-py3-none-any.whl'
        with zipfile.ZipFile(self.wheel, 'w') as archive:
            archive.writestr('sample-1.0.dist-info/METADATA', 'Metadata-Version: 2.1\nName: sample\nVersion: 1.0\n')
        self.manifest = bundle.manifest_for(self.folder, self.lock)
        self.save_manifest()

    def save_manifest(self):
        (self.folder / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def code_zip_fixture(self):
        import shutil
        source=self.root/'offline-app/packages'/self.wheel.name
        source.parent.mkdir(parents=True);shutil.copyfile(self.wheel,source)
        manifest=self.root/'offline-app/bundle-manifest.json';manifest.parent.mkdir(exist_ok=True)
        item={'schema_version':1,'bundle':self.manifest,'sources':{self.wheel.name:source.relative_to(self.root).as_posix()}}
        manifest.write_text(json.dumps(item),encoding='utf-8')
        return source,manifest,item

    def test_code_zip_reuses_verified_source_and_removes_temporary_bundle(self):
        import shutil
        self.code_zip_fixture();shutil.rmtree(self.folder)
        with code_zip.installation_bundle(self.root,self.folder) as target:
            self.assertNotEqual(target,self.folder)
            self.assertEqual(code_zip.verify_bundle(target,self.lock),self.manifest)
            self.assertTrue((target/self.wheel.name).is_file())
        self.assertFalse(target.exists());self.assertFalse(self.folder.exists())
        self.assertFalse((self.root/'.venv').exists())

    def test_code_zip_corrupt_missing_and_lfs_source_rejected(self):
        source,manifest,item=self.code_zip_fixture();original=source.read_bytes()
        for case in ('tampered','missing','lfs'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as target:
                source.write_bytes(original)
                if case=='tampered':source.write_bytes(original+b'tampered')
                elif case=='missing':source.unlink()
                else:source.write_bytes(b'version https://git-lfs.github.com/spec/v1\n')
                with self.assertRaises(code_zip.BundleError):code_zip.materialize(self.root,target)
                self.assertFalse((self.root/'.venv').exists())

    def test_code_zip_unsafe_source_or_changed_lock_rejected(self):
        source,manifest,item=self.code_zip_fixture()
        for location in ('../'+self.wheel.name,'/outside/'+self.wheel.name,'offline-app/packages/../../'+self.wheel.name):
            with self.subTest(location=location),tempfile.TemporaryDirectory() as target:
                item['sources'][self.wheel.name]=location;manifest.write_text(json.dumps(item))
                with self.assertRaisesRegex(code_zip.BundleError,'source_invalid'):code_zip.materialize(self.root,target)
        item['sources'][self.wheel.name]=source.relative_to(self.root).as_posix();manifest.write_text(json.dumps(item))
        self.lock.write_text('sample==2.0\n')
        with tempfile.TemporaryDirectory() as target,self.assertRaisesRegex(code_zip.BundleError,'fingerprint'):
            code_zip.materialize(self.root,target)

    def test_code_zip_never_falls_back_from_existing_invalid_wheelhouse(self):
        self.code_zip_fixture();self.wheel.write_bytes(b'tampered')
        with code_zip.installation_bundle(self.root,self.folder) as selected:
            self.assertEqual(selected,self.folder)
            with patch.object(installer.subprocess,'run') as run,self.assertRaises(installer.BundleError):
                installer.install(self.root,selected)
            run.assert_not_called()
        self.assertFalse((self.root/'.venv').exists())

    def test_complete_bundle_verifies(self):
        self.assertEqual(bundle.verify_bundle(self.folder, self.lock), self.manifest)

    def test_missing_wheel_rejected(self):
        self.wheel.unlink()
        with self.assertRaises(bundle.BundleError): bundle.verify_bundle(self.folder, self.lock)

    def test_corrupt_wheel_rejected(self):
        with self.wheel.open('ab') as stream: stream.write(b'tampered')
        with self.assertRaisesRegex(bundle.BundleError, 'integrity'): bundle.verify_bundle(self.folder, self.lock)

    def test_lock_mismatch_rejected(self):
        self.lock.write_text('sample==2.0\n', encoding='ascii')
        with self.assertRaisesRegex(bundle.BundleError, 'fingerprint'): bundle.verify_bundle(self.folder, self.lock)

    def test_unsafe_manifest_path_and_extra_files_rejected(self):
        self.manifest['files']['../escape.whl'] = self.manifest['files'].pop(self.wheel.name)
        self.save_manifest()
        with self.assertRaisesRegex(bundle.BundleError, 'manifest'): bundle.verify_bundle(self.folder, self.lock)
        self.manifest = bundle.manifest_for(self.folder, self.lock); self.save_manifest()
        (self.folder / 'unexpected.txt').write_text('extra', encoding='ascii')
        with self.assertRaisesRegex(bundle.BundleError, 'unexpected'): bundle.verify_bundle(self.folder, self.lock)

    def test_wrong_target_rejected(self):
        self.manifest['target'] = 'cp311-linux'; self.save_manifest()
        with self.assertRaisesRegex(bundle.BundleError, 'target'): bundle.verify_bundle(self.folder, self.lock)

    def test_existing_build_destination_untouched(self):
        with self.assertRaisesRegex(bundle.BundleError, 'destination_exists'):
            bundle.build_bundle(self.folder, self.lock)
        self.assertTrue(self.wheel.exists())


class OfflineInstallerTests(unittest.TestCase):
    setUp = OfflineBundleTests.setUp
    save_manifest = OfflineBundleTests.save_manifest

    def test_rejects_existing_environment_and_invalid_bundle_before_creation(self):
        existing=self.root/'.venv'; existing.mkdir()
        marker=existing/'keep.txt';marker.write_text('keep')
        with patch.object(installer.subprocess,'run') as run:
            with self.assertRaisesRegex(installer.InstallError,'not_overwritten'):
                installer.install(self.root,self.folder)
            self.assertEqual(marker.read_text(),'keep');run.assert_not_called()
            for name in ('../escape','elsewhere','.venv/child'):
                with self.subTest(name=name),self.assertRaises(installer.InstallError):
                    installer.install(self.root,self.folder,name)
            with patch.object(installer.sys,'version_info',(3,10,5)):
                with self.assertRaisesRegex(installer.InstallError,'python3104'):
                    installer.install(self.root,self.folder,'.venv-new')
            self.wheel.unlink()
            with self.assertRaises(installer.BundleError):
                installer.install(self.root,self.folder,'.venv-new')
            self.assertFalse((self.root/'.venv-new').exists());run.assert_not_called()

    def test_main_diagnostics_are_isolated_and_explicit_data_is_preserved(self):
        from contextlib import redirect_stdout
        import io
        seen=[]
        def fake_install(project, source, environment, data_dir, progress):
            data=Path(data_dir);self.assertTrue(data.is_dir())
            seen.append(data)
            progress.update(status='passed',company_real='not_tested')
        explicit=self.root/'explicit-data';explicit.mkdir()
        marker=explicit/'keep.txt';marker.write_text('keep')
        with patch.object(installer,'ROOT',self.root),patch.object(installer,'install',side_effect=fake_install),redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main(['--offline-bundle',str(self.folder)]),0)
            self.assertFalse(seen[-1].exists())
            self.assertEqual(installer.main(['--offline-bundle',str(self.folder),'--data-dir',str(explicit)]),0)
            self.assertEqual(seen[-1],explicit)
            self.assertEqual(marker.read_text(),'keep')

    def test_install_is_offline_only_failures_stop_and_lock_is_required(self):
        from contextlib import redirect_stdout
        import io
        from types import SimpleNamespace
        for case in ('success','create','pip','freeze'):
            report={};commands=[]
            def run(command,**kw):
                commands.append(command)
                self.assertEqual(kw['env']['PIP_CONFIG_FILE'],installer.os.devnull)
                failure=(case=='create' and 'venv' in command) or (case=='pip' and 'install' in command)
                return SimpleNamespace(returncode=1 if failure else 0,
                                       stdout='sample==9.0\n' if case=='freeze' else 'sample==1.0\n')
            with self.subTest(case=case),patch.object(installer.subprocess,'run',side_effect=run),redirect_stdout(io.StringIO()):
                if case=='success':
                    installer.install(self.root,self.folder,'.venv-'+case,progress=report)
                    self.assertEqual(report['status'],'passed')
                    self.assertEqual(report['full_regression'],'not_tested')
                    self.assertEqual(report['company_real'],'not_tested')
                else:
                    with self.assertRaises(installer.InstallError):
                        installer.install(self.root,self.folder,'.venv-'+case,progress=report)
                    self.assertEqual(report['status'],'failed')
                self.assertTrue(report['environment_created'])
                installs=[command for command in commands if 'install' in command]
                self.assertEqual(len(installs),0 if case=='create' else 1)
                for command in installs:
                    for flag in ('--isolated','--no-index','--no-deps','--no-cache-dir','--only-binary=:all:'):
                        self.assertIn(flag,command)
                    self.assertEqual(command[command.index('--find-links')+1],str(self.folder))
                if case=='pip':self.assertEqual(len(commands),3)


if __name__ == '__main__':
    unittest.main()
