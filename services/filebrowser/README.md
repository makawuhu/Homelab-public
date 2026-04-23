# FileBrowser

Web-based file manager for browsing and managing files on VM 101.

- **Host:** VM 101 (`192.168.x.5`)
- **Port:** 8085
- **External URL:** http://filebrowser.yourdomain.com
- **Runs as:** uid 1000
- **Storage:** Docker volume `filebrowser-data` (srv root) + `filebrowser-db` (BoltDB metadata)

> Access errors are OS-level permission issues, not FileBrowser user permissions. Files at `/mnt/media` must be readable by uid 1000.
