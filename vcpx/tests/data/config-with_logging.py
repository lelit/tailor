#!tailor
'''
[DEFAULT]
verbose = False

[project1]
root-directory = /tmp/tailor-tests
source = svn:source
target = darcs:target

[svn:source]
repository = svn://some.server/svn
module = project1

[darcs:target]
repository = ~/darcs/project1

[[logging]]

[formatters]
keys = dummy

[formatter_dummy]
format = DUMMY

[loggers]
keys = root

[logger_root]
level = INFO
handlers = dummy

[handlers]
keys = dummy

[handler_dummy]
class = StreamHandler
formatter = dummy
args = (sys.stdout,)
level = NOTSET
'''
