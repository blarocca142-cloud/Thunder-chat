# The code vault

Where code Thunder writes is kept, and how it gets off the phone.

## Storage

Files live on thunder-main at the absolute path

    /home/blayne/Thunder-chat/Thunder-chat-v3/thunder-main-api/thunder-data/code/<project>/<filename>

as real files in real directories - not rows in a database. That means the
overnight worker can compile them, `scp` works, a project zips with no export
step, and if the API is switched off the code is still sitting in a folder.

A project is just a directory. Code saved from a conversation goes into a
project named after that chat, so a week of work does not become one
undifferentiated pile of snippets. Anything unnamed lands in `scratch`.

Overwriting keeps one step back, as `.<filename>.prev`.

## Getting code off the phone

In the app, the **Code** tab (third in the bottom bar) lists projects, then
files, then the file. Code blocks in chat also carry a **Save** button next to
Copy, which files them into the vault.

Three routes out, for different jobs:

- **Save** writes into `Downloads/Thunder` on the phone, where a file manager
  or a USB cable will find it. On Android below 9 it goes to the app's own
  folder instead, because the public Downloads directory needs a permission
  this app does not request.
- **Send** opens the share sheet - into email, Drive, a text editor, anything.
- **Save all (.zip)** takes the whole project in one tap. This is the one to
  use to get work onto a laptop.

There is no USB port on any of this and no removable media involved: the phone
talks to Main over the LAN, and the file lands in the phone's own storage.

## Filenames

Thunder chooses them, so they are sanitised on the server: one path segment,
no directories, no dot-entries. A traversal attempt lands inside the project
rather than anywhere else on disk.

A path comment in the first lines wins - `# app/server.py` becomes
`server.py` - because models write those habitually. Otherwise the first class
or function name is used, with the extension implied by the fence tag
(```kotlin -> .kt).

## Endpoints

    POST   /code                              save a block
    GET    /code                              projects
    GET    /code/{project}                    files in one
    GET    /code/{project}/archive            the project as a zip
    GET    /code/{project}/file/{name}        content as JSON
    GET    /code/{project}/file/{name}/download   the file itself
    GET    /code/{project}/file/{name}/previous   what it said before
    DELETE /code/{project}/file/{name}
