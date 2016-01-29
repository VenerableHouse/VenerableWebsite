PasswordChangedEmail = \
"""
Hi {0},

Your password has been successfully changed. If you did not request a password
change, please let an IMSS rep know immediately.

Thanks!
The Ruddock Website
"""

ResetPasswordEmail = \
"""
Hi {0},

We have received a request to reset this account's password. If you didn't
request this change, let an IMSS rep know immediately. Otherwise, you can use
this link to change your password:

{1}

Your link will expire in {2}.

Thanks!
The Ruddock Website
"""

ResetPasswordSuccessfulEmail = \
"""
Hi {0},

Your password has been successfully reset. If you did not request a password
reset, please let an IMSS rep know immediately.

Thanks!
The Ruddock Website
"""

CreateAccountSuccessfulEmail = \
"""
Hi {0},

You have just created an account for the Ruddock website with the username
"{1}". If this was not you, please let an IMSS rep know immediately.

Thanks!
The Ruddock Website
"""

AddedToWebsiteEmail = \
"""
Hi {0},

You have been added to the Ruddock House Website. In order to access private
areas of our site, please complete registration by creating an account here:

{1}

If you have any questions or concerns, please find an IMSS rep or email us at
imss@ruddock.caltech.edu.

Thanks!
The Ruddock Website
"""

MembersAddedEmail = \
"""
The following members have been added to the Ruddock Website:

{0}

and the following members were skipped (they were already in the database):

{1}

You should run the email update script to add the new members.

Thanks!
The Ruddock Website
"""

ErrorCaughtEmail = \
"""
An exception was caught by the website. This is probably a result of a bad server configuration or bugs in the code, so you should look into this. This was the exception:

{}
"""
