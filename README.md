RuddockWebsite
==============

The Ruddock House Website.
Written in Flask using MySQL and Apache.
Live version can be found at: http://ruddock.caltech.edu


How to sync the constitution PDF?
-----------------------------------

We are using [submodules](http://git-scm.com/docs/git-submodule) to serve the constitution (via the [external repository](https://github.com/RuddockHouse/RuddockConstitution)). We did this to ensure all constitution changes are within the constitution repository.

When you first clone this repository, you must load the submodule. Fortunately, Git makes this easy. Simply run `git submodule init; git submodule update` from the project parent directory (`../RuddockWebsite/`).

After each change to the constitution (in the external repository), you will need to update the submodule by running `git submodule foreach git pull origin master` from the project parent directory. Once you update the submodule, you'll need to commit your changes. This results in a small diff to switch the submodule's reference commit to the new version.

Note: once we update to the newest version of Git (at least 1.8.2), we can update the submodule with `git submodule update --remote`. Until then, the foreach workaround will work fine.
