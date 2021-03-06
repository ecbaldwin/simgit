#!/usr/bin/env python

from simgit import repository

repository = repository.Repository()

master = repository.branch("master", color="#808080")
master.commit(message="First commit")
master.commit(message="Original branch point for feature")

anna = master.branch("anna", color="#ffb900")
anna.commit(message="Groundwork")
john = anna.branch("john", "#007dff")
anna.commit(message="Anna's part")
john.commit(message="John's part")
master.commit(message="Conflicting work on master")
anna.rebase(master)
john.rebase(master)
repository.render()
