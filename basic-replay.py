#!/usr/bin/env python

from simgit import repository

repository = repository.Repository()

master = repository.branch("master", color="#808080")
master.commit(message="First commit")
master.commit(message="Original branch point for feature")

development = master.branch("development", color="#007fff")
development.commit(message="Anna's Feature")
master.commit(message="John's conflicting feature")
development.replay(master)
# This should know that master is upstream and just fast forward
master.replay(development)
repository.render()
