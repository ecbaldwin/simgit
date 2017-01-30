#!/usr/bin/env python

from simgit import repository

repository = repository.Repository()

master = repository.branch("master", color="#808080")
master.commit(message="First commit")
master.commit(message="Original branch point for feature")

john = master.branch("john", color="#007dff")
john.commit(message="Collaborative Change")
anna = john.branch("anna", "#ffb900")
anna.replay(master, modify=True)
john.replay(master, modify=True)
repository.render()
