import cv2
import time

url = "https://stream.kuduskab.go.id/memfs/b2e6de86-4d67-4797-a6e8-7e57871d0a0a.m3u8"
cap = cv2.VideoCapture(url)
print("opened:", cap.isOpened())
if cap.isOpened():
    for i in range(20):
        ok, frame = cap.read()
        if ok and frame is not None:
            h, w = frame.shape[:2]
            print(f"frame {i}: OK {w}x{h}")
            cv2.imwrite(r"C:\Users\legion\flowsense\data\frame_test.jpg", frame)
            break
        else:
            print(f"frame {i}: read failed")
            time.sleep(0.5)
    cap.release()
