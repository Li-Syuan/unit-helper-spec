"""Materialize the single verified App wheel source without network access."""
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from offline_bundle import BundleError, digest, valid_name, verify_bundle


def materialize(project, destination):
    project, destination = Path(project).resolve(), Path(destination).resolve()
    manifest_path = project/'offline-app/bundle-manifest.json'
    try:
        if manifest_path.is_symlink() or manifest_path.stat().st_size > 2*1024*1024:
            raise BundleError('code_zip_manifest_invalid')
        item=json.loads(manifest_path.read_text('utf-8'))
        if set(item) != {'schema_version','bundle','sources'} or item['schema_version'] != 1:
            raise BundleError('code_zip_manifest_invalid')
        bundle, sources=item['bundle'], item['sources']
        if not isinstance(sources,dict) or set(sources) != set(bundle['files']):
            raise BundleError('code_zip_sources_incomplete')
        if destination.is_symlink() or any(destination.iterdir()):
            raise BundleError('code_zip_destination_not_empty')
        for name, location in sources.items():
            if not valid_name(name) or not isinstance(location,str):
                raise BundleError('code_zip_source_invalid')
            relative=PurePosixPath(location)
            if ('\\' in location or relative.is_absolute() or '..' in relative.parts
                    or relative.name != name or relative.parent.as_posix() != 'offline-app/packages'):
                raise BundleError('code_zip_source_invalid')
            source=project.joinpath(*relative.parts)
            if (not source.is_file() or any(project.joinpath(*relative.parts[:i]).is_symlink()
                    for i in range(1,len(relative.parts)+1))
                    or not source.resolve().is_relative_to(project)):
                raise BundleError('code_zip_source_missing_or_linked')
            with source.open('rb') as stream:
                if stream.read(64).startswith(b'version https://git-lfs.github.com/spec/v1'):
                    raise BundleError('code_zip_lfs_pointer_not_wheel')
            if digest(source) != bundle['files'][name]['sha256']:
                raise BundleError('code_zip_source_hash_mismatch')
            shutil.copyfile(source,destination/name)
        (destination/'manifest.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
        return verify_bundle(destination,project/'requirements.lock')
    except BundleError:
        raise
    except (OSError,ValueError,KeyError,TypeError):
        raise BundleError('code_zip_bundle_invalid_or_missing') from None


@contextmanager
def installation_bundle(project, requested):
    project, requested=Path(project).resolve(),Path(requested).resolve()
    # Existing or explicitly different bundles must pass their own integrity checks;
    # a corrupt or stale wheelhouse is never replaced by the Code ZIP source.
    if requested == project/'wheelhouse' and not os.path.lexists(requested):
        with tempfile.TemporaryDirectory(prefix='qa-code-wheels-') as temporary:
            materialize(project,temporary)
            print('Verified Code ZIP wheels: offline-app/packages; no downloads.',flush=True)
            yield Path(temporary)
    else:
        yield requested
