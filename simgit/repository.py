from __future__ import print_function

import abc
import collections
import contextlib
import hashlib
import itertools
import sys


class XmlText(object):
    def __init__(self):
        self._text = None

    def render(self):
        print(self._text, end="")

    @property
    def content(self):
        return self._text

    @content.setter
    def content(self, text):
        self._text = text


class XmlTag(object):
    def __init__(self, name):
        self._name = name
        self._attrs = {}
        self._children = []

    @property
    def attrs(self):
        return self._attrs

    @attrs.setter
    def attrs(self, attr_dict):
        self._attrs = attr_dict

    def render(self):
        print("<%s" % self._name, end="")
        for name, value in self.attrs.iteritems():
            print(" %s=\"%s\"" % (name, value), end="")
        if not self._children:
            print("/>", end="")
        else:
            print(">", end="")
            for child in self._children:
                child.render()
            print("</%s>" % self._name, end="")

    @contextlib.contextmanager
    def child(self, name):
        c = XmlTag(name)
        self._children.append(c)
        yield c

    @contextlib.contextmanager
    def text(self):
        c = XmlText()
        self._children.append(c)
        yield c


class XmlDoc(object):
    def __init__(self):
        self._root = None

    @contextlib.contextmanager
    def root(self, name):
        self._root = XmlTag(name)
        yield self._root

    def render(self):
        self._root.render()


class Commitish(object):
    __metaclass__ = abc.ABCMeta
    @abc.abstractmethod
    def commitish(self):
        """ The commit represented by this thing. """

    @abc.abstractmethod
    def name(self):
        """ The name """

    def __str__(self):
        return str(self.commitish())


class Commit(Commitish):
    LAST_SHA1 = ""

    def __init__(self,
                 parents,
                 message,
                 branch=None,
                 sha1=None,
                 ancestors=None,
                 replaces=None):
        # Just faking a progression through sha1s
        self._parents = parents
        if ancestors is None:
            ancestors = []
        if replaces is None:
            replaces = []
        self._ancestors = ancestors
        self._replaces = replaces
        self._message = message
        self._color = branch.color
        self._branch_num = branch.num
        self._sha1 = sha1
        if sha1 is None:
            self._sha1 = hashlib.sha1(Commit.LAST_SHA1).hexdigest()
            Commit.LAST_SHA1 = self.sha1
        self._x = None
        self._y = None
        self._max_x = sys.maxsize

    @property
    def branch_num(self):
         return self._branch_num

    @property
    def x(self):
         return self._x

    @x.setter
    def x(self, value):
        self._x = value

    @property
    def y(self):
         return self._y

    @y.setter
    def y(self, value):
        self._y = value

    @property
    def max_x(self):
         return self._max_x

    @max_x.setter
    def max_x(self, value):
        self._max_x = value

    def __str__(self):
        return self._sha1

    @classmethod
    def Rebase(cls, parents, ancestors, commit, branch=None):
        return cls(parents=parents, ancestors=ancestors, branch=branch, message=commit.message)

    @classmethod
    def Replay(cls, parents, replaces, commit, branch=None):
        return cls(parents=parents, replaces=replaces, branch=branch, message=commit.message)

    @property
    def sha1(self):
        return self._sha1

    def name(self):
        return self.sha1

    @property
    def parents(self):
        return self._parents

    @property
    def ancestors(self):
        return self._ancestors

    def add_ancestor(self, ancestor):
        self._ancestors.append(ancestor)

    @property
    def replaces(self):
        return self._replaces

    def add_replaces(self, replaces):
        self._replaces.append(replaces)

    @property
    def message(self):
        return self._message

    def commitish(self):
        return self

    @property
    def color(self):
        return self._color


class Color(object):
    def __init__(self, r, g, b):
        self._r = r
        self._g = g
        self._b = b

    @classmethod
    def FromString(cls, string):
        if isinstance(string, Color):
            return string
        if string.startswith("#"):
            return cls(r=int(string[1:3], 16),
                       g=int(string[3:5], 16),
                       b=int(string[5:7], 16))
        raise Exception("Bad color string")

    def __str__(self):
        return "#%02x%02x%02x" % (self._r, self._g, self._b)

    def __eq__(self, o):
        return self._r == o._r and self._g == o._g and self._b == o._b

    def lighten(self):
        high = int("ff", 16)
        new_r = self._r + (high - self._r) * 3 / 4
        new_g = self._g + (high - self._g) * 3 / 4
        new_b = self._b + (high - self._b) * 3 / 4
        return self.__class__(r=new_r, g=new_g, b=new_b)


def dfs_visit(branches, visit_parents=True, visit_ancestors=False, visit_replaces=False):
    if not isinstance(branches, list):
        branches = [branches]

    seen = set()
    def visit(commit):
        if commit.sha1 in seen:
            return
        seen.add(commit.sha1)

        if visit_ancestors:
            for parent in commit.ancestors:
                branches.append(parent)
        parents = []
        if visit_parents:
            parents += sorted(commit.parents, key=lambda c: c.branch_num)
        if visit_replaces:
            parents += commit.replaces
        for parent in parents:
            for child in visit(parent):
                yield child

        yield commit

    while branches:
        branch = branches[0]
        branches = branches[1:]
        for commit in visit(branch.commitish()):
            yield commit


class Branch(Commitish):
    NUM_BRANCHES = 0
    def __init__(self, repository, head, name, color):
        self._repository = repository
        self._head = head
        self._name = name
        self._color = Color.FromString(color)
        self._downstreams = set()
        Branch.NUM_BRANCHES += 1
        self._num = Branch.NUM_BRANCHES

    @property
    def head(self):
        return self._head

    @property
    def name(self):
        return self._name

    @property
    def num(self):
        return self._num

    @property
    def color(self):
        return self._color

    def commitish(self):
        return self.head

    def commit(self, message):
        if self._head:
            parents = [self._head]
        else:
            parents = []
        commit = Commit(parents=parents, message=message, branch=self)
        self._head = commit
        return commit

    def cherry_pick(self, commit):
        if self._head:
            parents = [self._head]
        else:
            parents = []
        rebased = Commit.Rebase(parents=parents, ancestors=[commit], branch=self, commit=commit)
        self._head = rebased
        return rebased

    def branch(self, name, color=None):
        # TODO Do I really want to make it the same color or a different color?
        if color is None:
            color = self.color
        new_branch =  self._repository.branch(name=name, head=self.commitish(), color=color)
        self._downstreams.add(new_branch)
        return new_branch

    def merge(self, others, message=None):
        if isinstance(others, Commitish):
            others = [others]
        for other in others:
            if self.commitish() == other.commitish():
                raise Exception("Can't merge a branch into itself")
            if not isinstance(other, Commitish):
                raise Exception("Merging something that isn't like a commit")

        # See if fast-forward is possible
        if len(others) == 1:
            other = others[0]
            for commit in dfs_visit(other):
                if commit == self.commitish():
                    # If you want the commit to show up on the master lane in
                    # gray, uncomment this.
                    # other.commitish()._color = self.color
                    self.reset(other)
                    return self.commitish()

        parents = [self.commitish()]
        for other in others:
            parents.append(other.commitish())
        if message is None:
            message = "Merging %s into %s" % ([o.name for o in others], self.name)
        merge_commit = Commit(parents, message, branch=self)
        self._head = merge_commit
        return merge_commit

    def reset(self, branch):
        self._head = branch.commitish()

    def rebase(self, other, fixups=None):
        if fixups is None:
            fixups = set()
        if not isinstance(other, Commitish):
            raise Exception("Rebasing to something that isn't like a commit")
        old = self.commitish()
        self.reset(other)

        # Mark the commits reachable from the other branch
        seen = set()
        for commit in dfs_visit(other.commitish()):
            seen.add(commit.sha1)

        # List the commits that aren't on the other branch
        to_rebase = []
        for commit in dfs_visit(old):
            if commit.sha1 in seen:
                continue
            if commit.sha1 not in fixups:
                to_rebase.append(commit)

        for commit in to_rebase:
            self.cherry_pick(commit)

        self.commitish().add_ancestor(old)
        return self.commitish()

    def fixup_rebase(self, original, fixup):
        self.rebase(original.parents[0], fixups={fixup.sha1})

    # This is almost the same as the other one.
    def replay_merge(self, commits):
        if self._head:
            parents = [self._head]
        else:
            parents = []
        replayed = Commit.Replay(parents=parents, replaces=commits, branch=self, commit=commits[0])
        self._head = replayed
        return replayed

    def replay_commit(self, commit):
        if self._head:
            parents = [self._head]
        else:
            parents = []
        replayed = Commit.Replay(parents=parents, replaces=[commit], branch=self, commit=commit)
        self._head = replayed
        return replayed

    def replay_amend(self):
        old = self.commitish()
        replayed = Commit.Replay(parents=old.parents, replaces=[old], branch=self, commit=old)
        self._head = replayed
        replayed.add_ancestor(old)

    def replay(self, other, fixups=None):
        # Replay has a direction. Always replay downstream onto upstream.
        if other in self._downstreams:
            old = self.commitish()
            self.reset(other)
            self.replay(old)
            # Accessing the private _color attr. I know.
            # self.commitish()._color = self.color
            self.commitish().add_ancestor(old)
            return self.commitish()

        # Check if this is a fast-forward situation.
        for commit in dfs_visit(self.commitish()):
            if commit == other.commitish():
                if not fixups:
                    return

        other_commits = {c for c in dfs_visit(other.commitish())}
        my_commits = {c for c in dfs_visit(self.commitish())}
        common_commits = other_commits & my_commits

        # Map each commit to all old revisions of it by following only replaces pointers
        revisions = collections.defaultdict(set)
        for commit in (other_commits|my_commits) - common_commits:
            for revision in dfs_visit(commit, visit_replaces=True, visit_parents=False):
                if len(revisions[revision]):
                    continue
                if len(revision.replaces):
                    # Pull the set from the old revision to this one.
                    # When we're finished the set will have all of the revisions of any given commit.
                    revisions[revision] = revisions[revision.replaces[0]]
                revisions[revision].add(revision)

        # Basically, fixups just get dropped for now.
        skip_commits = other_commits | set(fixups or [])
        originals = set(fixups.values()) if fixups else set()
        to_replay = [c for c in dfs_visit(self.commitish())
                     if c not in skip_commits]

        # Reset the branch to the other to begin replaying commits onto it.
        old = self.commitish()
        self.reset(other)

        # First, play the upstream commits
        # Until we have to create a new commit, we can just fast-forward through these
        seen = set()
        fast_forward = True
        for commit in dfs_visit(other.commitish()):
            if commit in common_commits:
                continue

            seen.add(commit)

            all_revs = revisions[commit]
            same_change_set = all_revs & my_commits
            if not same_change_set:
                if fast_forward:
                    self.reset(commit)
                    continue

                self.replay_commit(commit)
                continue

            if len(same_change_set) > 1:
                raise Exception("There shouldn't be two old revisions of this change in a branch")
            other_rev = same_change_set.pop()
            seen.add(other_rev)

            # See if the downstream is reachable from the upstream
            for c in dfs_visit(commit, visit_replaces=True, visit_parents=False):
                if c == other_rev:
                    if fast_forward:
                        self.reset(commit)
                        break
                    self.replay_commit(commit)
                    break
            else:
                # See if the upstream is reachable from the downstream
                for c in dfs_visit(other_rev, visit_replaces=True, visit_parents=False):
                    if c == commit:
                        if fast_forward:
                            self.reset(other_rev)
                            break
                        self.replay_commit(other_rev)
                        break
                else:
                    # Neither is reachable from the other. Merge them.
                    fast_forward = False
                    self.replay_merge([commit, other_rev])

        for commit in to_replay:
            if commit in seen:
                continue
            if fast_forward:
                if self.commitish() not in commit.parents:
                    fast_forward = False
                if commit in originals:
                    fast_forward = False
            if fast_forward:
                self.reset(commit)
                continue
            self.replay_commit(commit)

        self.commitish().add_ancestor(old)
        return self.commitish()

    def fixup_replay(self, original, fixups):
        self.replay(original.parents[0], fixups=fixups)


class Repository(object):
    def __init__(self):
        self._branches = collections.OrderedDict()

    def branch(self, name, head=None, color=None):
        if name in self._branches:
            raise Exception("That branch already exists.")
        b = Branch(repository=self,
                   head=head,
                   name=name,
                   color=color)
        self._branches[name] = b
        return b

    def place(self):
        grid = collections.defaultdict(
            lambda: collections.defaultdict(
                lambda: None))

        # First place the branches in lanes. This traversal doesn't follow
        # replaces pointers as part of DFS because I want obsoleted branches to
        # appear below active branches.
        lane = 1
        last_commit = None
        for commit in self.dfs_visit(visit_ancestors=True):
            if not commit.parents:
                commit.y = lane
            else:
                # Advance the lane if this is a new branch
                for parent in commit.parents:
                    if parent == last_commit:
                        if commit.color != commit.parents[0].color:
                            lane += 1
                        break
                else:
                    lane += 1
                commit.y = lane
            last_commit = commit

        # Now with the branches
        for commit in self.dfs_visit(visit_ancestors=True, visit_replaces=True):
            if not commit.parents:
                commit.x = 1
            else:
                minimum_x = max(p.x + 1 for p in itertools.chain(commit.parents,commit.replaces))
                # Take the next spot in the same lane
                commit.x = minimum_x
            grid[commit.y][commit.x] = commit
            print("Placing %s at %s,%s" % (commit.sha1, commit.x, commit.y), file=sys.stderr)
            for parent in commit.parents:
                parent.max_x = min(commit.x-1, parent.max_x)
            # Try to pull parents closer if possible
            # TODO Do this recursively?
            for parent in commit.parents:
                if not any(grid[parent.y][x] for x in range(parent.x+1, commit.x)):
                    parent.x = min(commit.x-1, parent.max_x)

        return grid

    def render(self, active_branches=None):
        xml = XmlDoc()
        grid = self.place()
        with xml.root(name='svg') as svg:
            height = len(grid)
            width = max(max(x for x in lane) for lane in grid.values())
            svg.attrs = {
                "height": str(60 * (height + 1)),
                "width": str(60 * (width + 1)),
                "xmlns": "http://www.w3.org/2000/svg",
                "xmlns:svg": "http://www.w3.org/2000/svg",
                "stroke": "null",
                "style": "vector-effect: non-scaling-stroke;",
            }
            if not active_branches:
                active_branches = self._branches.values()
            active = {c for c in dfs_visit(active_branches)}

            for commit in self.dfs_visit(visit_ancestors=True):
                for parent in commit.replaces:
                    with svg.child("path") as line:
                        line.attrs = {
                            "id": "%s-%s" % (parent.sha1, commit.sha1),
                            "stroke": parent.color.lighten() if parent not in active else parent.color,
                            "d": "M%s,%s C%s,%s %s,%s %s,%s" % (60 * parent.x, 60 * parent.y,
                                                                60 * commit.x, 60 * (parent.y + commit.y)/2,
                                                                60 * parent.x, 60 * (parent.y + commit.y)/2,
                                                                60 * commit.x, 60 * commit.y),
                            "stroke-width": "8",
                            "stroke-dasharray": "5, 5",
                            "fill": "none",
                        }
                for parent in commit.parents:
                    with svg.child("path") as line:
                        line.attrs = {
                            "id": "%s-%s" % (parent.sha1, commit.sha1),
                            "stroke": parent.color.lighten() if commit not in active else parent.color,
                            "d": "M%s,%s C%s,%s %s,%s %s,%s" % (60 * parent.x, 60 * parent.y,
                                                                60 * commit.x, 60 * (parent.y + commit.y)/2,
                                                                60 * parent.x, 60 * (parent.y + commit.y)/2,
                                                                60 * commit.x, 60 * commit.y),
                            "stroke-width": "8",
                            "fill": "none",
                        }

            for commit in self.dfs_visit(visit_ancestors=True):
                with svg.child("circle") as circle:
                    circle.attrs = {
                        "id": "commit-" + commit.sha1,
                        "cy": str(60 * commit.y),
                        "cx": str(60 * commit.x),
                        "fill": commit.color.lighten() if commit not in active else commit.color,
                        "stroke": "#aaaaaa",
                        "r": "12",
                        "stroke-linecap": "null",
                        "stroke-linejoin": "null",
                        "stroke-dasharray": "null",
                        "stroke-width": "0",
                    }
                    with circle.child("title") as title:
                        with title.text() as text:
                            text.content = "%s %s" % (commit.sha1[0:6], commit.message)

        xml.render()

    def dfs_visit(self, visit_parents=True, visit_ancestors=True, visit_replaces=False):
        return dfs_visit(self._branches.values(),
                         visit_parents=visit_parents,
                         visit_ancestors=visit_ancestors,
                         visit_replaces=visit_replaces)
