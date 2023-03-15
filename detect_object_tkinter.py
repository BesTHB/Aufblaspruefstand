import cv2
import numpy as np
import tkinter as tk
from PIL import Image, ImageTk

# src: https://www.youtube.com/watch?v=lbgl2u6KrDU
# src: https://www.youtube.com/watch?v=UlM2bpqo_o0
# src: https://www.youtube.com/watch?v=tk9war7_y0Q
# src: https://stackoverflow.com/questions/32342935/using-opencv-with-tkinter (https://stackoverflow.com/a/43159588)
# src: https://github.com/jumejume1/python-camera1/blob/main/color_thresholding.py

class Application:
    def __init__(self):
        # connect with webcam
        # (iterate through numbers in order to find the correct webcam, if multiple are available)
        self.cap = cv2.VideoCapture(0)
        self.current_image = None

        # set displayed size of the webcam image/video
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # setup aruco marker
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

        # init list of images (original and filtered)
        self.imgs = [None, None]
        self.img_displayed = 1

        # setup tkinter
        self.win = tk.Tk()
        self.win.title('Blubb')
        self.win.protocol('WM_DELETE_WINDOW', self.destructor)

        # init image panel
        self.panel = tk.Label(self.win)
        self.panel.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # create sliders for hsv
        self.hsv_min_max = [[60, 90], [95, 255], [50, 255]]
        self.h_min = tk.IntVar()
        self.h_max = tk.IntVar()
        self.s_min = tk.IntVar()
        self.s_max = tk.IntVar()
        self.v_min = tk.IntVar()
        self.v_max = tk.IntVar()
        self.slider_h_min = tk.Scale(self.win, label='h_min', orient='horizontal', from_=0, to=255, variable=self.h_min, command=lambda x: None)
        self.slider_h_max = tk.Scale(self.win, label='h_max', orient='horizontal', from_=0, to=255, variable=self.h_max, command=lambda x: None)
        self.slider_s_min = tk.Scale(self.win, label='s_min', orient='horizontal', from_=0, to=255, variable=self.s_min, command=lambda x: None)
        self.slider_s_max = tk.Scale(self.win, label='s_max', orient='horizontal', from_=0, to=255, variable=self.s_max, command=lambda x: None)
        self.slider_v_min = tk.Scale(self.win, label='v_min', orient='horizontal', from_=0, to=255, variable=self.v_min, command=lambda x: None)
        self.slider_v_max = tk.Scale(self.win, label='v_max', orient='horizontal', from_=0, to=255, variable=self.v_max, command=lambda x: None)
        self.slider_h_min.set(self.hsv_min_max[0][0])
        self.slider_s_min.set(self.hsv_min_max[1][0])
        self.slider_v_min.set(self.hsv_min_max[2][0])
        self.slider_h_max.set(self.hsv_min_max[0][1])
        self.slider_s_max.set(self.hsv_min_max[1][1])
        self.slider_v_max.set(self.hsv_min_max[2][1])
        self.slider_h_min.grid(row=1, column=0, sticky='nsew')
        self.slider_h_max.grid(row=1, column=1, sticky='nsew')
        self.slider_s_min.grid(row=2, column=0, sticky='nsew')
        self.slider_s_max.grid(row=2, column=1, sticky='nsew')
        self.slider_v_min.grid(row=3, column=0, sticky='nsew')
        self.slider_v_max.grid(row=3, column=1, sticky='nsew')

        # create slider for findContour
        self.minArea = tk.DoubleVar()
        self.slider_minArea = tk.Scale(self.win, label='minArea', orient='horizontal', from_=0, to=5000, variable=self.minArea, command=lambda x: None)
        self.slider_minArea.set(2000)
        self.slider_minArea.grid(row=4, column=0, sticky='nsew', padx=10, pady=10)

        # create reset button
        self.btn_reset = tk.Button(self.win, text='reset', command=self.reset_values)
        self.btn_reset.grid(row=5, column=0, sticky='nsew', padx=10, pady=10)

        # create button for switching between showing the original or the filtered image
        self.btn_switch_img = tk.Button(self.win, text='switch img', command=self.switch_img)
        self.btn_switch_img.grid(row=5, column=1, sticky='nsew', padx=10, pady=10)

        # start video loop
        self.video_loop()

    def reset_values(self):
        self.slider_h_min.set(self.hsv_min_max[0][0])
        self.slider_s_min.set(self.hsv_min_max[1][0])
        self.slider_v_min.set(self.hsv_min_max[2][0])
        self.slider_h_max.set(self.hsv_min_max[0][1])
        self.slider_s_max.set(self.hsv_min_max[1][1])
        self.slider_v_max.set(self.hsv_min_max[2][1])
        self.slider_minArea.set(400)

    def switch_img(self):
        if self.img_displayed == 0:
            self.img_displayed = 1
        elif self.img_displayed == 1:
            self.img_displayed = 0

    def video_loop(self):
        # get current webcam imgage
        ret, self.imgs[0] = self.cap.read()
        if ret:
            hsv_min = np.array([self.h_min.get(), self.s_min.get(), self.v_min.get()])
            hsv_max = np.array([self.h_max.get(), self.s_max.get(), self.v_max.get()])

            img_hsv = cv2.cvtColor(self.imgs[0], cv2.COLOR_BGR2HSV)
            color_mask = cv2.inRange(img_hsv, hsv_min, hsv_max)
            self.imgs[1] = cv2.bitwise_and(self.imgs[0], self.imgs[0], mask=color_mask)

            # detect aruco markers in current webcam image
            corners, ids, _ = cv2.aruco.detectMarkers(self.imgs[0], self.aruco_dict, parameters=self.aruco_params)

            # draw polygon around aruco markers
            int_corners = np.intp(corners)
            cv2.polylines(self.imgs[self.img_displayed], int_corners, True, (0, 255, 0), 2)

            try:
                # calculate the length of the polygon around the first detected aruco marker
                aruco_perimeter = cv2.arcLength(corners[0], True)  # in pixels

                # translate pixels to mm
                # (since the aruco marker is a square of side length 50mm, the length of the surrounding polygon must be 200mm)
                pixel_mm_ratio = aruco_perimeter / 200

                # calculate center of polygon and widths of aruco marker and display a text
                x, y = corners[0][0].mean(axis=0)
                s1, s2 = self.calc_aruco_widths(corners[0][0])
                cv2.putText(self.imgs[self.img_displayed], f'ID: {ids[0][0]}', (int(x), int(y)), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)
                cv2.putText(self.imgs[self.img_displayed], f'[pixel] {s1:.2f} x {s2:.2f}', (int(x), int(y)-30), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)
                cv2.putText(self.imgs[self.img_displayed], f'[mm] {s1/pixel_mm_ratio:.2f} x {s2/pixel_mm_ratio:.2f}', (int(x), int(y)-15), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0), 1)

            # if currently no aruco marker is detected in the webcam image, corners[0] will throw an IndexError
            except IndexError:
                pass

            # detect contours, conversion to grayscale is necessary for findContours
            img_gray = cv2.cvtColor(self.imgs[1], cv2.COLOR_BGR2GRAY)
            contours, _ = cv2.findContours(img_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in contours:
                area = cv2.contourArea(c)
                if area > self.minArea.get():
                    rect = cv2.minAreaRect(c)
                    (x, y), (w, h), angle = rect
                    box = cv2.boxPoints(rect)
                    box = np.intp(box)
                    cv2.polylines(self.imgs[self.img_displayed], [box], True, (0, 0, 255), 2)
                    cv2.putText(self.imgs[self.img_displayed], f'[pixel] width: {w:.1f}, height: {h:.1f}', (int(x), int(y)+15), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)
                    try:
                        cv2.putText(self.imgs[self.img_displayed], f'[mm] width: {w/pixel_mm_ratio:.2f}, height: {h/pixel_mm_ratio:.2f}', (int(x), int(y)+30), cv2.FONT_HERSHEY_PLAIN, 1, (255, 0, 0), 1)
                    except UnboundLocalError:
                        # if pixel_mm_ratio is not present, pass
                        pass

            # prepare imgage for tkinter
            cv2image = cv2.cvtColor(self.imgs[self.img_displayed], cv2.COLOR_BGR2RGBA)
            self.current_image = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=self.current_image)
            self.panel.imgtk = imgtk
            self.panel.config(image=imgtk)

        self.win.after(30, self.video_loop)   # call same function after 30 ms

    def calc_aruco_widths(self, c):
        x0, y0 = c[0]
        x1, y1 = c[1]
        x2, y2 = c[2]
        x3, y3 = c[3]
        wx = 0.5*np.sqrt( (x0+x3-x1-x2)**2 + (y0+y3-y1-y2)**2 )
        wy = 0.5*np.sqrt( (x0+x1-x2-x3)**2 + (y0+y1-y2-y3)**2 )
        return wx, wy

    def destructor(self):
        # close connection to webcam and destroy webcam window
        self.win.destroy()
        self.cap.release()
        cv2.destroyAllWindows()

app = Application()
app.win.mainloop()