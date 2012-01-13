from __future__ import absolute_import
from __future__ import with_statement

import sys

from contextlib import contextmanager
from string import Template
from subprocess import Popen, PIPE

from . import __version__
from . import files
from .utils import changedir, codewrap, maybe_flag, maybe_opt, say, tempdir
from .versions import Version


class Bundle(object):

    def __init__(self, name, description=None, requires=None, version=None,
            author=None, author_email=None, url=None, platforms=None,
            license=None, setup_template=None, readme_template=None):
        self.name = name
        self.description = description or "autogenerated bundle"
        self.requires = requires or []
        self.version = version or "1.0"
        self.author = author or ""
        self.author_email = author_email or ""
        self.url = url or ""
        self.platforms = platforms or ["all"]
        self.license = license or "BSD"
        self._setup_template = setup_template
        self._readme_template = readme_template
        self._pypi = None

    def register(self, repository=None, show_response=None, strict=None, **_):
        self.sync_with_released_version()
        self.run_setup_command(
                *self._register_cmd(repository, show_response, strict))

    def _register_cmd(self, repository, show_response, strict):
        return (["register"]
              + maybe_opt("-r", repository)
              + maybe_flag("--show-response", show_response)
              + maybe_flag("--strict", strict))

    def upload(self, repository=None, show_response=None, strict=None,
            sign=None, identity=None, formats=None, **_):
        self.run_setup_command(
                *self._register_cmd(repository, show_response, strict)
                +self._sdist_cmd(formats)
                +self._upload_cmd(repository, show_response, sign, identity))

    def _upload_cmd(self, repository, show_response, sign, identity):
        return (["upload"]
              + maybe_opt("-r", repository)
              + maybe_opt("-s", sign)
              + maybe_opt("-i", identity)
              + maybe_flag("--show_response", show_response))

    def _sdist_cmd(self, formats):
        return ["sdist"] + maybe_opt("--formats=", formats)

    def upload_fix(self, *args, **kwargs):
        self.bump_if_already_released()
        self.upload(*args, **kwargs)

    def run_setup_command(self, *argv):
        with self.render_to_temp() as setup_name:
            say(self._call([sys.executable, setup_name] + list(argv)))

    def _call(self, argv):
        say("$ %s" % ' '.join(argv))
        return Popen(argv, stdout=PIPE).communicate()[0]

    def sync_with_released_version(self):
        self.version = self.version_info.sync_with_released_version()

    def bump_if_already_released(self):
        self.version = self.version_info.bump_if_released()

    def version_released(self):
        return self.version_info.is_released

    def render_setup(self):
        return Template(self.setup_template).substitute(**self.stash)

    def render_readme(self):
        return Template(self.readme_template).substitute(**self.stash)

    @contextmanager
    def render_to_temp(self, setup_filename="setup.py",
                             readme_filename="README"):
        with tempdir() as dir:
            with changedir(dir):
                with open(setup_filename, "w") as setup:
                    setup.write(self.render_setup())
                    setup.flush()
                    with open(readme_filename, "w") as readme:
                        readme.write(self.render_readme())
                    yield setup_filename

    def upload_if_missing(self):
        if not self.version_exists():
            self.upload()

    def __repr__(self):
        return "<Bundle: %s v%s" % (self.name, self.version)

    @property
    def version_info(self):
        return Version(self.name, self.version)

    @property
    def stash(self):
        title = " - ".join([self.name, self.description])
        return dict(self.__dict__,
                    title=title,
                    title_h1='=' * len(title),
                    bundle_version=__version__,
                    requires_i2=codewrap(repr(self.requires), i=5),
                    requires_i24=codewrap(repr(self.requires), i=24))

    @property
    def setup_template(self):
        if self._setup_template is None:
            self._setup_template = files.slurp("setup.py.t")
        return self._setup_template

    @property
    def readme_template(self):
        if self._readme_template is None:
            self._readme_template = files.slurp("README.t")
        return self._readme_template
