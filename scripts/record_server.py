import http.server
import socketserver
import os
import json
import subprocess
import shutil
import sys

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(BASE_DIR, "temp_frames")
DOCS_ASSETS = os.path.join(BASE_DIR, "..", "docs", "assets")
FRONTEND_PUBLIC = os.path.join(BASE_DIR, "..", "frontend", "public")

os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(DOCS_ASSETS, exist_ok=True)
os.makedirs(FRONTEND_PUBLIC, exist_ok=True)

class FrameHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Frame-Index')
        self.end_headers()

    def do_POST(self):
        if self.path == "/clear_frames":
            shutil.rmtree(FRAMES_DIR, ignore_errors=True)
            os.makedirs(FRAMES_DIR, exist_ok=True)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "cleared"}')

        elif self.path == "/save_frame":
            content_length = int(self.headers.get('Content-Length', 0))
            frame_data = self.rfile.read(content_length)
            
            frame_idx = int(self.headers.get('X-Frame-Index', 0))
            frame_filename = os.path.join(FRAMES_DIR, f"frame_{frame_idx:04d}.png")
            with open(frame_filename, "wb") as f:
                f.write(frame_data)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        elif self.path == "/encode_video":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            params = json.loads(post_data.decode('utf-8'))
            fps = params.get("fps", 60)
            total_frames = params.get("total_frames", 240)
            
            print(f"\n[INFO] Starting fast FFmpeg encode of {total_frames} frames at {fps} fps...", flush=True)
            
            input_pattern = os.path.join(FRAMES_DIR, "frame_%04d.png")
            webm_temp = os.path.join(BASE_DIR, "output.webm")
            mp4_temp = os.path.join(BASE_DIR, "output.mp4")

            try:
                # 1. Encode ultra-fast high-quality MP4 (H.264, CRF 18, preset fast)
                print("[INFO] Encoding MP4 (H.264)...", flush=True)
                cmd_mp4 = [
                    "ffmpeg", "-y",
                    "-framerate", str(fps),
                    "-i", input_pattern,
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    mp4_temp
                ]
                res_mp4 = subprocess.run(cmd_mp4, capture_output=True, text=True)
                if res_mp4.returncode != 0:
                    print(f"[ERROR] MP4 failed:\n{res_mp4.stderr}", flush=True)
                    raise RuntimeError(f"MP4 encode failed: {res_mp4.stderr}")
                
                # 2. Encode fast high-quality WebM (VP9, realtime deadline, cpu-used 4, threads)
                print("[INFO] Encoding WebM (VP9)...", flush=True)
                cmd_webm = [
                    "ffmpeg", "-y",
                    "-framerate", str(fps),
                    "-i", input_pattern,
                    "-c:v", "libvpx-vp9",
                    "-crf", "22",
                    "-b:v", "0",
                    "-deadline", "realtime",
                    "-cpu-used", "4",
                    "-threads", "8",
                    "-pix_fmt", "yuv420p",
                    webm_temp
                ]
                res_webm = subprocess.run(cmd_webm, capture_output=True, text=True)
                if res_webm.returncode != 0:
                    print(f"[ERROR] WebM failed:\n{res_webm.stderr}", flush=True)
                    raise RuntimeError(f"WebM encode failed: {res_webm.stderr}")
                
                # Copy to target destinations
                for dest in [DOCS_ASSETS, FRONTEND_PUBLIC]:
                    shutil.copy2(webm_temp, os.path.join(dest, "borromean_banner.webm"))
                    shutil.copy2(mp4_temp, os.path.join(dest, "borromean_banner.mp4"))
                    frame_zero = os.path.join(FRAMES_DIR, "frame_0000.png")
                    if os.path.exists(frame_zero):
                        shutil.copy2(frame_zero, os.path.join(dest, "borromean_snapshot.png"))
                    
                # Create SVG banner embedding
                svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">
  <rect width="1920" height="1080" fill="#000000"/>
  <foreignObject width="1920" height="1080">
    <video xmlns="http://www.w3.org/1999/xhtml" 
           src="borromean_banner.webm" 
           autoplay="true" 
           loop="true" 
           muted="true" 
           playsinline="true" 
           style="width: 100%; height: 100%; object-fit: contain; background: #000000; display: block;" />
  </foreignObject>
</svg>
'''
                with open(os.path.join(DOCS_ASSETS, "borromean_banner.svg"), "w", encoding="utf-8") as f:
                    f.write(svg_content)
                with open(os.path.join(FRONTEND_PUBLIC, "borromean_banner.svg"), "w", encoding="utf-8") as f:
                    f.write(svg_content)
                    
                print(f"[SUCCESS] Ultra-smooth 60fps WebM, MP4, and SVG exported to {DOCS_ASSETS} and {FRONTEND_PUBLIC}", flush=True)
                
                # Cleanup temp video files and frames
                if os.path.exists(webm_temp): os.remove(webm_temp)
                if os.path.exists(mp4_temp): os.remove(mp4_temp)
                shutil.rmtree(FRAMES_DIR, ignore_errors=True)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except Exception as e:
                print(f"[FATAL] Encoding exception: {e}", flush=True)
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

if __name__ == "__main__":
    server = ThreadedHTTPServer(('0.0.0.0', PORT), FrameHandler)
    print(f"Multi-Threaded Frame Encoder Server running on http://127.0.0.1:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.", flush=True)
        server.server_close()
