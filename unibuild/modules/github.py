# Copyright (C) 2015 Sebastian Herbord.  All rights reserved.
# Copyright (C) 2016 - 2019 Mod Organizer contributors.
#
# This file is part of Mod Organizer.
#
# Mod Organizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mod Organizer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mod Organizer.  If not, see <http://www.gnu.org/licenses/>.
import sys
import os
import urllib.request
import json
import subprocess
import logging
from config import config
from unibuild.modules.git import Clone
from unibuild.modules.urldownload import URLDownload


def Popen(cmd, **kwargs):
    pc = ''
    if 'cwd' in kwargs:
        try:
            pc += os.path.relpath(kwargs['cwd'], os.path.abspath('..'))
        except ValueError:
            pc += kwargs['cwd']
    pc += '>'
    for arg in cmd:
        pc += ' ' + arg
    print(pc)
    return subprocess.Popen(cmd,**kwargs)


class Release(URLDownload):
    def __init__(self, author, project, version, filename, extension="zip", tree_depth=0):
        super(Release, self) \
            .__init__("https://github.com/{author}/{project}/releases/download/{version}/"
                      "{filename}.{extension}".format(author=author,
                                                      project=project,
                                                      version=version,
                                                      filename=filename,
                                                      extension=extension), tree_depth)
        self.set_destination("{}-{}".format(project, version))


class Tag(URLDownload):
    def __init__(self, author, project, tag, version, extension="zip", tree_depth=1):
        super(Tag, self).__init__("https://github.com/{author}/{project}/archive/{tag}.{extension}"
                                             .format(author=author,
                                                     project=project,
                                                     tag=tag,
                                                     extension=extension), tree_depth)
        self.set_destination("{}-{}".format(project, tag))


class Source(Clone):
    def __init__(self, author, project, branch="master", feature_branch=None, pr_label=None, super_repository=None, update=True, commit=None, shallowclone=False):
        self.__author = author
        self.__project = project
        if config['shallowclone']:
            self.shallowclone = True
        if pr_label is not None:
            self.__pr_label = pr_label

        super(Source, self).__init__("https://github.com/{author}/{project}.git".format(author=author, project=project),
                                     branch, feature_branch, super_repository, update, commit, shallowclone)

        self.set_destination(project)

    def process(self, progress):
        super(Source, self).process(progress)

        if self.__pr_label is not None:
            url = "https://api.github.com/repos/{}/{}/pulls".format(self.__author, self.__project)
            response = urllib.request.urlopen(url)
            data = json.loads(response.read())
            filtered_data = list(filter(lambda x: x["head"]["label"] == self.__pr_label, data))
            sys.stdout.write(filtered_data.__str__())
            if len(filtered_data) > 0:
                repo_url = filtered_data["head"]["repo"]["html_url"]
                repo_branch = filtered_data["head"]["ref"]
                proc = Popen([config['paths']['git'], "remote", "add", "pr", repo_url],
                             cwd=self._context["build_path"],
                             env=config["__environment"])
                proc.communicate()
                if proc.returncode != 0:
                    logging.error("failed to add pr remote %s (returncode %s)", repo_url, proc.returncode)
                    return False

                proc = Popen([config['paths']['git'], "checkout", repo_branch, "pr/{}".format(repo_branch)],
                             cwd=self._context["build_path"],
                             env=config["__environment"])
                proc.communicate()
                if proc.returncode != 0:
                    logging.error("failed to checkout pr branch %s (returncode %s)", repo_branch, proc.returncode)
                    return False
