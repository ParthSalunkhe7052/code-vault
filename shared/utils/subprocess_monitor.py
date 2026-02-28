import sys
import threading
import queue
import select

def _read_output_thread(pipe, output_queue):
    """Thread function to read from pipe and put lines in queue."""
    try:
        for line in iter(pipe.readline, b""):
            output_queue.put(line)
    finally:
        pipe.close()

def wait_for_output_with_timeout(process, timeout=1.0):
    """Cross-platform way to wait for output with timeout.

    On Unix: uses select.select()
    On Windows: uses threading and queue

    Returns True if output is available, False otherwise.
    """
    if sys.platform == "win32":
        # On Windows, select.select() doesn't work with pipes
        # Use a queue-based approach with threads
        if not hasattr(process, "_output_queue"):
            process._output_queue = queue.Queue()
            process._reader_thread = threading.Thread(
                target=_read_output_thread, args=(process.stdout, process._output_queue)
            )
            process._reader_thread.daemon = True
            process._reader_thread.start()

        # Check if there's data in the queue (non-blocking)
        return not process._output_queue.empty()
    else:
        # On Unix-like systems, use select.select()
        if process.stdout:
            readable, _, _ = select.select([process.stdout], [], [], timeout)
            return bool(readable)
        return False

def readline_from_process(process):
    """Cross-platform way to read a line from process stdout."""
    if sys.platform == "win32":
        # On Windows, read from the queue
        if hasattr(process, "_output_queue"):
            try:
                return process._output_queue.get(block=False)
            except queue.Empty:
                return None
        return None
    else:
        # On Unix-like systems, read directly
        if process.stdout:
            return process.stdout.readline()
        return None
