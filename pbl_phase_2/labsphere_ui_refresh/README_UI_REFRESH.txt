LabSphere UI Refresh + Virtual Hypervisor

1. Install Flask if needed: python -m pip install flask
2. Run from this folder: python app.py
3. Open http://127.0.0.1:5000

Demo logins:
Admin: admin / admin123
Staff: staff / staff123

Virtual hypervisor:
Open Virtual hypervisor from the workspace navigation to create virtual machine profiles. Choose an OS label, vCPU count, memory and disk, then start, stop, restart, or delete stopped machine profiles. VM records are stored in the included SQLite database. This feature simulates VM management only; it does not connect to a real hypervisor, install guest operating systems, or allocate host resources.

Existing database data is preserved; the app creates the virtual_machines table on startup. This is a local academic demo, not production-hardened software.
