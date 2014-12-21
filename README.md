RuddockWebsite
==============

The Ruddock House Website.
Written in Flask using MySQL and Apache.
Live version can be found at: http://ruddock.caltech.edu


How to update the constitution PDF?
-----------------------------------

We are using [submodules](http://git-scm.com/docs/git-submodule) to serve the constitution (via the [external repository](https://github.com/RuddockHouse/RuddockConstitution)). We did this to ensure all constitution changes are within the constitution repository.

After each change to the constitution (in the external repository), you will need to update the submodule. Fortunately, Git makes this easy. Simply run `git submodule foreach git pull origin master` from the project parent directory (`../RuddockWebsite/`).

Note: once we update to the newest version of Git (at least 1.8.2), we can simply use `git submodule update --remote` from the project parent directory. Until then, this workaround will work fine.
