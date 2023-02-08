# Allow to run multiple lines in a recipe in the same shell.
.ONESHELL:

SRCDIR=algorandsmc
TESTDIR=tests

TARGETDIRS=$(SRCDIR)/ demos/ $(TESTDIR)/

PROTOC=protoc

compile-smc:
	$(PROTOC) --proto_path=./protos --python_out=$(SRCDIR) --pyi_out=$(SRCDIR) protos/smc.proto

compile-protobuf: compile-smc

autoflake:
	poetry run autoflake -r --in-place --remove-unused-variables --remove-all-unused-imports $(TARGETDIRS)

black:
	poetry run black $(TARGETDIRS) --exclude '.*_pb2\.pyi?'

isort:
	poetry run isort $(TARGETDIRS)

# line-too-long is disabled because black already takes care of that.
pylint:
	poetry run pylint --disable=fixme --disable=too-few-public-methods --disable=line-too-long --ignore-patterns '.*_pb2\.pyi?' $(TARGETDIRS)

consistent-format: autoflake black isort

correct-format: consistent-format pylint

tests: compile-protobuf
	poetry run pytest -x --cov=$(SRCDIR) $(TESTDIR)

coverage-report:
	poetry run coverage report -m --sort=Cover > coverage-report.txt
	cat coverage-report.txt

# .PHONY indicates which targets are not connected to the generation of one or more files.
.PHONY: autoflake black isort mypy pylint consistent-format correct-format tests coverage
