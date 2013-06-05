#!/usr/bin/env python3

# Copyright 2013 Csaba Hoch
# Copyright 2013 Adam Rutkowski
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Recommended reading:
#
# - http://ctags.sourceforge.net/FORMAT
# - http://vimdoc.sourceforge.net/htmldoc/tagsrch.html#tags-file-format

# The Tags ets table has the following scheme:
#
#     {{TagName, FilePath, Kind, Scope}, TagAddress}
#
# Or in more readable notation:
#
#     {TagName, FilePath, Kind, Scope} -> TagAddress
#
# Examples of entries (and the tags output generated from them):
#
#     {ErlFileName, FilePath, global, $F} -> TagAddress
#
#         myfile.erl  ./myfile.erl  1;"  F
#
#     {HrlFileName, FilePath, global, $F} -> TagAddress
#
#         myfile.hrl  ./myfile.hrl  1;"  F
#
#     {ModName, FilePath, global, $M} -> TagAddress
#
#         myfile  ./myfile.erl  1;"  M
#
#     {FuncName, FilePath, local, $f} -> TagAddress
#
#         f  ./mymod.erl  /^f\>/;"  f  file:
#
#     {FuncName, FilePath, global, $f} -> TagAddress
#
#         mymod:f  ./mymod.erl  /^f\>/;"  f
#
#     {Record, FilePath, local, $r} -> TagAddress
#
#         myrec  ./mymod.erl  /^-record\.\*\<myrec\>/;"  r  file:
#
#     {Record, FilePath, global, $r} -> TagAddress
#
#         myrec  ./myhrl.hrl  /^-record\.\*\<myrec\>/;"  r
#
#     {Macro, FilePath, local, $d} -> TagAddress
#
#         mymac  ./mymod.erl  /^-record\.\*\<myrec\>/;"  d  file:
#
#     {Macro, FilePath, global, $d} -> TagAddress
#
#         mymac  ./myhrl.hrl  /^-record\.\*\<myrec\>/;"  d


import argparse
import sys
import fnmatch
import os
import re
import fileinput


##### Utility functions #####


def log(*messages):
    if args.verbose:
        print(*messages, file=sys.stderr)


##### Handling files #####


def create_tags(files):
    tags = {}
    log('Tags dictionary created.')
    try:
        files.pop(files.index('-'))
        read_stdin = True
    except ValueError:
        read_stdin = False

    if read_stdin:
        for line in fileinput.input():
            process_dir_or_file(line.strip(), tags)

    for file in files:
        process_dir_or_file(file, tags)

    return tags


def process_dir_or_file(file, tags):
    if os.path.isdir(file):
        process_dir(file, tags)
    else:
        add_tags_from_file(file, tags)


def process_dir(main_dir, tags):
    for root, dirs, files in os.walk(main_dir):
        for filename in fnmatch.filter(files, '*.[eh]rl'):
            add_tags_from_file(os.path.join(root, filename), tags)


##### Adding tags #####


def add_tags_from_file(file, tags):
    log("Processing file:", file)
    basename = os.path.basename(file)
    name_and_ext = os.path.splitext(basename)
    add_file_tag(tags, file, basename, name_and_ext)
    for line in fileinput.input(file):
        scan_tags(file, name_and_ext, line, tags)


func_re = re.compile("^([a-z][a-zA-Z0-9_@]*)\\s*\\(")
recmac_re = re.compile("^-\\s*(record|define)\\s*\\(\\s*([a-zA-Z0-9_@]*)\\b")

def scan_tags(file, name_and_ext, line, tags):
    func_match = re.match(func_re, line)
    if func_match:
        add_func_tags(tags, file, name_and_ext, func_match.group(1))
        return

    recmac_match = re.match(recmac_re, line)
    if recmac_match:
        add_recmac_tag(tags, file, name_and_ext, recmac_match.group(1),
                       recmac_match.group(2))


def add_file_tag(tags, file, basename, name_and_ext):
    # myfile.hrl <tab> ./myfile.hrl <tab> 1;"  F
    # myfile.erl <tab> ./myfile.erl <tab> 1;"  F
    # myfile <tab> ./myfile.erl <tab> 1;"  M
    add_tag(tags, basename, file, '1', 'global', 'F')
    if name_and_ext[1] == '.erl':
        add_tag(tags, name_and_ext[0], file, '1', 'global', 'M');


def add_func_tags(tags, file, name_and_ext, func_name):
    log('Function definition found:', func_name)

    # Global entry:
    # mymod:f <tab> ./mymod.erl <tab> /^f\>/
    add_tag(tags, name_and_ext[0] + ":" + func_name, file,
            "/^" + func_name + "\\>/", 'global', 'f')

    # Static (or local) entry:
    # f <tab> ./mymod.erl <tab> /^f\>/ <space><space> ;" <tab> file:
    add_tag(tags, func_name, file, "/^" + func_name + "\\>/", 'local', 'f')

# File contains a macro or record called Name; add this information to Tags.
def add_recmac_tag(tags, file, name_and_ext, attribute, name):
    if attribute == 'record':
        log("Record found:", name),
        kind = 'r';
    elif attribute == 'define':
        log("Macro found:", name),
        kind = 'd'
    scope = 'global' if name_and_ext[1] == '.hrl' else 'local'

    # myrec  ./mymod.erl  /^-record\.\*\<myrec\>/;"  r  file:
    # myrec  ./myhrl.hrl  /^-record\.\*\<myrec\>/;"  r
    # myrec  ./mymod.erl  /^-define\.\*\<mymac\>/;"  m  file:
    # myrec  ./myhrl.hrl  /^-define\.\*\<mymac\>/;"  m
    add_tag(tags, name, file,
            "/^-\\s\\*" + attribute + "\\s\\*(\\s\\*" + name + "\\>/",
            scope, kind)
    
def add_tag(tags, tag, file, tagaddress, scope, kind):
    tags.setdefault((tag, file, kind, scope), tagaddress)


##### Writing tags into a file #####


def tags_to_file(tags, tagsfile):
    header = "!_TAG_FILE_SORTED\t1\t/0=unsorted, 1=sorted/\n"
    with open(tagsfile, 'w') as f:
        f.write(header)
        for tag_entry in sorted(tags.items()):
            f.write(tag_to_str(tag_entry))

def tag_to_str(tag_entry):
    ((tag, file, kind, scope), tagaddress) = tag_entry
        
    scopestr = '' if scope == 'global' else '\tfile:'
    return (tag + "\t" +
            file + "\t" +
            tagaddress + ";\"\t" +
            kind +
            scopestr + "\n")

##### Parse arguments #####


descr = """\
description:
  vim-erlang-tags.py creates a tags file that can be used by Vim. The
  directories given as arguments are searched (recursively) for *.erl and *.hrl
  files, which will be scanned. The files given as arguments are also scanned.
  The default is to search in the current directory.
"""

epilog = """
examples:
  $ vim-erlang-tags.py
  $ vim-erlang-tags.py .  # Same
  $ find . -name '*.[he]rl' | vim-erlang-tags.py -  # Equivalent to the above
  $ vim-erlang-tags.py /path/to/project1 /path/to/project2
"""

def parse_args():
    parser = argparse.ArgumentParser(description=descr,
                                     epilog=epilog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-o', '--output', dest='tagsfilename',
                        help='Tags file name.',
                        action='store', default='tags')
    parser.add_argument('-v', '--verbose', dest='verbose',
                        help='Verbose output',
                        action='store_true', default=False)
    parser.add_argument('files', nargs='*', default=['.'])
    return parser.parse_args()

def main():
    log('Arguments:', args)
    descr = ('description: it does nothing yet')
    tags = create_tags(args.files) 
    tags_to_file(tags, args.tagsfilename)

if __name__ == '__main__':
    args = parse_args()
    main()
