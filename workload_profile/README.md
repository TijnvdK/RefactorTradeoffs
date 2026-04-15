1. Install Xdebug
```bash
sudo apt-get install php-xdebug
```
2. Modify the Xdebug configuration file to include the following lines:
```ini
xdebug.mode = trace
xdebug.start_with_request=yes
xdebug.output_dir=/tmp/xdebug_traces
xdebug.trace_format=1
```
3. Run the application to generate the Xdebug trace file.
4. Parse the generated Xdebug trace file using the `parse_xdebug_trace.py`
script.
