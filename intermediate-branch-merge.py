#!/usr/bin/env python

from simgit import repository

repository = repository.Repository()

master = repository.branch("master", color="#808080")
master.commit(message="First commit")
master.commit(message="Original branch point for feature")

development = master.branch("development", color="#007fff")
development.commit(message="John's first change")
master.commit(message="Anna's conflicting feature")
original = development.merge(master)
development.commit(message="John's second change")
fixup = development.commit(message="John's fixup to his first change")

master.commit(message="Anna's second conflicting feature")
development.merge(master)
master.merge(development)
repository.render()
