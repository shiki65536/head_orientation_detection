import math
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import json
import os
import tkinter.filedialog
import glob


def head_orientation_vis(keypoints, epsilon=1e-8, threshold=200):
    # Define the keypoints
    right_eye_v = keypoints[5] == 2
    left_eye_v = keypoints[8] == 2
    right_shoulder_v = keypoints[11] == 2
    left_shoulder_v = keypoints[17] == 2
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    if right_eye[1] <=0 or left_eye[1] <= 0:
        return None
    # double check hand visibility
    right_hand_x, right_hand_y, right_hand_v = keypoints[30], keypoints[31], keypoints[32]
    right_shoulder_x, right_shoulder_y = keypoints[15], keypoints[16]
    distance_right = ((right_hand_x - right_shoulder_x) ** 2 + (right_hand_y - right_shoulder_y) ** 2) ** 0.5
    if distance_right < threshold:
        right_shoulder_v = 2

    # double check shoulder visibility
    left_hand_x, left_hand_y, left_hand_v = keypoints[39], keypoints[40], keypoints[41]
    left_shoulder_x, left_shoulder_y = keypoints[18], keypoints[19]
    distance_left = ((left_hand_x - left_shoulder_x) ** 2 + (left_hand_y - left_shoulder_y) ** 2) ** 0.5
    if distance_left < threshold:
        left_shoulder_v = 2

    # Calculate midpoint X coordinate between head and neck
    midpoint_x = (head[0] + neck[0]) / 2

    # Determine if both eyes are to the right of the midpoint
    eyes_right = right_eye[0] >= midpoint_x and left_eye[0] >= midpoint_x

    # Determine if both eyes are to the left of the midpoint
    eyes_left = right_eye[0] <= midpoint_x and left_eye[0] <= midpoint_x


    # Check visibility conditions and adjust angle based on head_neck x offset
    if right_eye_v and left_eye_v and right_shoulder_v and left_shoulder_v:
        # Adjust angle based on eyes position relative to midpoint
        if eyes_right:
            return 45
        elif eyes_left:
            return -45
        else:
            return 0
    elif right_eye_v and left_eye_v and right_shoulder_v:
        return 45
    elif right_eye_v and left_eye_v and left_shoulder_v:
        return -45
    elif right_eye_v and right_shoulder_v:
        return 90
    elif left_eye_v and left_shoulder_v:
        return -90
    elif not right_eye_v and not left_eye_v:
        if eyes_right:
            return 135
        elif eyes_left:
            return -135
        else:
            return 180
    elif right_shoulder_v:
        return 135
    elif left_shoulder_v:
        return -135
    else:
        return None  # In case none of the conditions are met


def head_orientation_math(keypoints, epsilon=1e-8, threshold=200, tolerance=500):
    # Define the keypoints
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    head_neck_x_offset = head[0] - neck[0]

    # Calculate vectors
    neck_to_head = (head[0] - neck[0], head[1] - neck[1])
    neck_to_right_eye = (right_eye[0] - neck[0], right_eye[1] - neck[1])
    neck_to_left_eye = (left_eye[0] - neck[0], left_eye[1] - neck[1])

    # Calculate angles between vectors
    angle_neck_to_right_eye = math.atan2(neck_to_right_eye[1], neck_to_right_eye[0] )#+ epsilon)
    angle_neck_to_left_eye = math.atan2(neck_to_left_eye[1], neck_to_left_eye[0] )#+ epsilon)

    # Calculate the average angle
    angle_radians = (angle_neck_to_right_eye + angle_neck_to_left_eye) / 2

    # Convert the angle from radians to degrees
    angle_degrees = math.degrees(angle_radians)

    # Calculate vertical distance between two eyes and head
    vertical_distance = abs(neck_to_head[1])

    # Adjust angle based on the vertical distance
    angle_adjustment = 0.1 * vertical_distance  # You can adjust the multiplier as needed
    angle_degrees += angle_adjustment


    # Adjust angle based on facing or being against the camera
    angle_degrees = (angle_degrees + 360) % 360

    # Additional adjustment for the front-facing angle
    angle_degrees -= 270

    if 10 >= angle_degrees >= -10:
        angle_degrees = 0
    elif -40 <= angle_degrees < -10:
        angle_degrees = -30
    elif -80 <= angle_degrees < -40:
        angle_degrees = -60
    elif -100 <= angle_degrees < -80:
        angle_degrees = -90
    # elif -110 <= angle_degrees < -100:
    #     angle_degrees = -120
    # elif -165 <= angle_degrees < -110:
    #     angle_degrees = -150
    # elif angle_degrees < -170 or 170 < angle_degrees:
    #     angle_degrees = 180
    elif 10 < angle_degrees <= 40:
        angle_degrees = 30
    elif 40 < angle_degrees <= 80:
        angle_degrees = 60
    elif 80 < angle_degrees <= 100:
        angle_degrees = 90
    # elif 100 < angle_degrees <= 155:
    #     angle_degrees = 120
    # elif 155 < angle_degrees <= 170:
    #     angle_degrees = 150
    else:
        angle_degrees = 180

    return angle_degrees


def combined_head_orientation(keypoints, epsilon=1e-8, threshold=200, tolerance=500):
    vis_result = head_orientation_vis(keypoints, epsilon, threshold)
    math_result = head_orientation_math(keypoints, epsilon, threshold, tolerance)

    # Define the keypoints
    right_eye_v = keypoints[5] == 2
    left_eye_v = keypoints[8] == 2
    right_shoulder_v = keypoints[11] == 2
    left_shoulder_v = keypoints[17] == 2
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    # if right_eye[1] <= 0 or left_eye[1] <= 0:
    #     return None

    # Calculate midpoint X coordinate between head and neck
    midpoint_x = (head[0] + neck[0]) / 2

    # Determine if both eyes are to the right of the midpoint
    eyes_right = right_eye[0] >= midpoint_x and left_eye[0] >= midpoint_x

    # Determine if both eyes are to the left of the midpoint
    eyes_left = right_eye[0] <= midpoint_x and left_eye[0] <= midpoint_x

    # # Check visibility conditions and adjust angle based on head_neck x offset
    if right_eye_v and left_eye_v and right_shoulder_v and left_shoulder_v:
        # Adjust angle based on eyes position relative to midpoint
        if eyes_right:
            return math_result
            return (math_result + vis_result) / 2 #45
        elif eyes_left:
            return math_result
            return (math_result + vis_result ) /2 #-45
        else:
            return 0
            return math_result / 2
    elif right_eye_v and left_eye_v and right_shoulder_v:
        return math_result
        return (math_result + vis_result) / 2 #math_result #45
    elif right_eye_v and left_eye_v and left_shoulder_v:
        return math_result
        return (math_result + vis_result) / 2  #math_result #-45
    elif right_eye_v and right_shoulder_v:
        return 90
        return (math_result + vis_result) / 2  #90
    elif left_eye_v and left_shoulder_v:
        return -90
        return (math_result + vis_result) / 2 #-90
    elif not right_eye_v and not left_eye_v:
        if eyes_right:
            return 180 - math_result
            return (math_result + vis_result) / 2  #180 - math_result #135
        elif eyes_left:
            return -180 - math_result
            return (math_result + vis_result) / 2  #-180 - math_result #-135
        else:
            return 180
            return (math_result + vis_result) / 2 #180
    elif right_shoulder_v:
        return 180 - math_result
        return (math_result + vis_result) / 2  #180 - math_result #135
    elif left_shoulder_v:
        return -180 - math_result
        return (math_result + vis_result) / 2  #-180 - math_result #-135
    else:
        return None  # In case none of the conditions are met


def get_arrow(angle):
    if angle is None:
        return "Out of screen"
    elif -22 <= angle <= 22:
        return "↓"
    elif 22 < angle <= 67:
        return "↘"
    elif 67 < angle <= 112:
        return "→"
    elif 112 < angle <= 157:
        return "↗"
    elif 157 < angle <= 180:
        return "↑"
    elif -67 <= angle < -22:
        return "↙"
    elif -112 <= angle < -67:
        return "←"
    elif -157 <= angle < -112:
        return "↖"
    elif -180 <= angle < -157:
        return "↑"
    else:
        return "Invalid angle"


class ImageViewer(tk.Tk):
    def __init__(self, images, annotations):
        super().__init__()

        self.images = images
        self.annotations = annotations
        self.current_image_index = 0
        self.results = []

        self.show_skeleton = True
        self.show_keypoints = True
        self.show_box = True

        # Adjust the window width to screen width
        self.geometry(f"{self.winfo_screenwidth()}x1")

        # Create a canvas to display the image
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Load the first image
        self.load_image(self.current_image_index)

        # Bind the keyboard events
        self.bind("<Left>", self.prev_image)
        self.bind("<Right>", self.next_image)

        # JSON
        self.load_new_json_button = tk.Button(self, text="Load New JSON", command=self.load_new_json)
        self.load_new_json_button.pack(side=tk.LEFT)

        # GO TO FRAME
        self.frame_entry = tk.Entry(self, width=10)
        self.frame_entry.pack(side=tk.LEFT)
        self.goto_button = tk.Button(self, text="Go to Frame", command=self.goto_frame)
        self.goto_button.pack(side=tk.LEFT)

        #save
        self.save_button = tk.Button(self, text="Save Results", command=self.process_frames)
        self.save_button.pack(side=tk.LEFT)

        self.stop_button = tk.Button(self, text="Stop Processing", command=self.stop_processing)
        self.stop_button.pack(side=tk.LEFT)

        self.process_all_button = tk.Button(self, text="Process All", command=self.process_all_jsons)
        self.process_all_button.pack(side=tk.LEFT)

        self.toggle_skeleton_button = tk.Button(self, text="Toggle Skeleton", command=self.toggle_skeleton)
        self.toggle_skeleton_button.pack(side=tk.LEFT)

        self.toggle_keypoints_button = tk.Button(self, text="Toggle Keypoints", command=self.toggle_keypoints)
        self.toggle_keypoints_button.pack(side=tk.LEFT)

        self.toggle_box_button = tk.Button(self, text="Toggle Box", command=self.toggle_box)
        self.toggle_box_button.pack(side=tk.LEFT)


        #self.process_frames()


    def load_and_resize_image(self, image_path):
        with Image.open(image_path) as img:
            # Get the screen width
            screen_width = self.winfo_screenwidth()

            # Calculate the scaling factor for width
            scale_factor = screen_width / img.width

            # Calculate the new image dimensions
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)

            # Resize the image
            img = img.resize((new_width, new_height))

            # Convert PIL Image to ImageTk
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

            # Adjust the window height to fit the image height
            self.geometry(f"{new_width}x{new_height}")

            # window size
            control_panel_height = 50  # 50px
            window_height = new_height + control_panel_height
            self.geometry(f"{new_width}x{window_height}")

            return img, scale_factor


    def draw_keypoints(self, keypoints, scale_factor):
        # Indices of joints to be displayed
        indices_to_draw = [1, 2, 3, 4, 5, 6, 7]  # Based on the list you provided

        for i in range(len(keypoints) // 3):
            if i in indices_to_draw:
                x, y, v = keypoints[i * 3], keypoints[i * 3 + 1], keypoints[i * 3 + 2]
                x *= scale_factor
                y *= scale_factor

                # Adjust colors or shapes based on visibility
                if v == 2:  # Visible
                    self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill='white')
                elif v == 1:  # Occluded
                    self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill='black')
                # Add an else statement if you want to handle the invisible joints differently
        # for i in range(0, len(keypoints), 3):
        #     x, y, v = keypoints[i:i + 3]
        #     x *= scale_factor
        #     y *= scale_factor
        #     if v == 2:  # If visibility is 2 (visible)
        #         self.canvas.create_oval(x-2, y-3, x+2, y+2, fill='white')
        #     elif v == 1:  # If visibility is 1 (occluded)
        #         self.canvas.create_oval(x-2, y-2, x+2, y+2, fill='black')

    def draw_skeleton(self, keypoints, scale_factor, color):
        # Define the pairs of keypoints to connect
        keypoint_pairs = [
            (0, 4),  # Head to Neck
            (1, 2),  # Right Eye to Left Eye
            (3, 4),  # Right Shoulder to Neck
            (5, 4),  # Left Shoulder to Neck
            (4, 8),  # Neck to Center Hip
            (3, 6),  # Right Shoulder to Right Elbow
            (6, 9),  # Right Elbow to Right Wrist
            (5, 7),  # Left Shoulder to Left Elbow
            (7, 12)  # Left Elbow to Left Wrist
        ]

        # Draw the lines
        for start_idx, end_idx in keypoint_pairs:
            # Multiply by 3 because each keypoint has x, y, visibility
            start_keypoint = keypoints[start_idx * 3:start_idx * 3 + 3]
            end_keypoint = keypoints[end_idx * 3:end_idx * 3 + 3]

            # Check if both keypoints are visible; if so, draw the line
            if start_keypoint[2] > 0 and end_keypoint[2] > 0:
                start_x, start_y, _ = start_keypoint
                end_x, end_y, _ = end_keypoint
                # Apply scaling
                start_x *= scale_factor
                start_y *= scale_factor
                end_x *= scale_factor
                end_y *= scale_factor

                # Calculate the distance between keypoints
                distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

                # Draw line if the distance is less than 500
                if distance <= 500:
                    self.canvas.create_line(start_x, start_y, end_x, end_y, fill=color, width=2)

    def draw_head_box(self, keypoints, scale_factor, track_id):
        head_index = 0
        right_eye_index = 1
        left_eye_index = 2
        neck_index = 4

        # Get the coordinates of the keypoints and apply scale_factor
        head = (keypoints[head_index * 3] * scale_factor, keypoints[head_index * 3 + 1] * scale_factor)
        right_eye = (keypoints[right_eye_index * 3] * scale_factor, keypoints[right_eye_index * 3 + 1] * scale_factor)
        left_eye = (keypoints[left_eye_index * 3] * scale_factor, keypoints[left_eye_index * 3 + 1] * scale_factor)
        neck = (keypoints[neck_index * 3] * scale_factor, keypoints[neck_index * 3 + 1] * scale_factor)

        # Determine the upper and lower bounds based on the y coordinates of head, right eye, left eye, and neck
        upper_bound_y = max(head[1], right_eye[1], left_eye[1], neck[1])
        lower_bound_y = min(head[1], right_eye[1], left_eye[1], neck[1])

        # Calculate the bounding box around the head
        head_box_size = 5  # You can adjust this size based on your preference
        head_box_min_x = min(head[0], right_eye[0], left_eye[0], neck[0]) - head_box_size
        head_box_max_x = max(head[0], right_eye[0], left_eye[0], neck[0]) + head_box_size

        # Set head_box_min_y to the upper_bound_y and head_box_max_y to lower_bound_y
        head_box_min_y = upper_bound_y
        head_box_max_y = lower_bound_y * 0.9

        # Draw the bounding box around the head
        if self.show_box:
            self.canvas.create_rectangle(head_box_min_x, head_box_min_y, head_box_max_x, head_box_max_y,  outline='black', width=3)
            self.canvas.create_rectangle(head_box_min_x, head_box_min_y, head_box_max_x, head_box_max_y, outline='white',
                                     width=1)
        # self.canvas.create_text(head_box_min_x, head_box_max_y - 10 , text=f"id:{track_id}", font=('Arial', 10),
        #                      anchor=tk.NW, fill='white')
        return (head_box_min_x, head_box_min_y, head_box_max_y)


    def toggle_skeleton(self):
        self.show_skeleton = not self.show_skeleton
        self.load_image(self.current_image_index)

    def toggle_keypoints(self):
        self.show_keypoints = not self.show_keypoints
        self.load_image(self.current_image_index)

    def toggle_box(self):
        self.show_box = not self.show_box
        self.load_image(self.current_image_index)

    def display_head_orientation(self, keypoints, cord_x, cord_y, cord_y_top, track_id):
        orientation = combined_head_orientation(keypoints)
        arrow = get_arrow(orientation)
        info_text = f"{arrow} ({orientation}°)"
        id_text = f"id:{track_id}"
        # self.canvas.create_text(cord_x, cord_y , text=info_text, font=('Arial', 9), anchor=tk.NW, fill='white')

        self.canvas.create_text(cord_x + 1, cord_y + 1, text=info_text, font=('Arial', 10), anchor=tk.NW, fill="black")
        self.canvas.create_text(cord_x, cord_y, text=info_text, font=('Arial', 10), anchor=tk.NW, fill="white")

        self.canvas.create_text(cord_x + 1, cord_y_top - 10 + 1, text=id_text, font=('Arial', 8), anchor=tk.NW, fill="black")
        self.canvas.create_text(cord_x, cord_y_top - 10, text=id_text, font=('Arial', 8), anchor=tk.NW, fill="white")

        result = {
            "image_id": self.current_image_index,
            "track_id": track_id,
            "orientation": orientation,
            "arrow": arrow,
            "cord_x": cord_x,
            "cord_y": cord_y,
            "cord_y_top": cord_y_top
        }
        self.results.append(result)

        # Print the head orientation for each track_id to the console
        print(f"Track ID: {track_id}  Orientation: {orientation}°")

    def load_image(self, index):
        # Clear the canvas
        self.canvas.delete("all")

        # Load and show the image
        img_path = "images/" + self.images[index]['file_name']
        img, scale_factor = self.load_and_resize_image(img_path)

        # Print the image_id
        image_id = self.images[index]['id']
        print(f"===================================== Image ID: {image_id} =====================================")

        # Display Image ID on the canvas
        canvas_width = self.winfo_screenwidth()
        self.canvas.create_text(canvas_width // 2, 10, text=f"Image ID: {image_id}", font=('Arial', 12), anchor=tk.N, fill="white")

        # color
        colors = ["salmon", "turquoise", "orange", "chartreuse", "orchid"]
        track_id_to_color = {}

        # Determine head orientation and display it on the canvas
        for annotation in self.annotations:
            if annotation['image_id'] == image_id:
                keypoints = annotation['keypoints']
                track_id = annotation.get("track_id", "N/A")
                if track_id not in track_id_to_color:
                    track_id_to_color[track_id] = colors[len(track_id_to_color) % len(colors)]

                color = track_id_to_color[track_id]

                if self.show_skeleton:
                    self.draw_skeleton(keypoints, scale_factor, color)
                if self.show_keypoints:
                    self.draw_keypoints(keypoints, scale_factor)
                #self.draw_bounding_box(keypoints, scale_factor, track_id)
                (cord_x, cord_y, cord_y_top) = self.draw_head_box(keypoints, scale_factor, track_id)

                # self.display_head_orientation(keypoints, min(keypoints[0::3]) * scale_factor, max(keypoints[1::3]) * scale_factor, track_id)
                self.display_head_orientation(keypoints, cord_x, cord_y, cord_y_top, track_id)

        # Update the canvas scroll region
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def prev_image(self, event):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image(self.current_image_index)

    def next_image(self, event):
        if self.current_image_index < len(self.images) - 1:
            self.current_image_index += 1
            self.load_image(self.current_image_index)

    def goto_frame(self):
        frame_number = self.frame_entry.get()
        try:
            frame_number = int(frame_number)
            if 0 <= frame_number < len(self.images):
                self.current_image_index = frame_number
                self.load_image(self.current_image_index)
            else:
                print("Frame number out of range")
        except ValueError:
            print("Invalid frame number")

    def process_frames(self):
        while self.current_image_index < len(self.images):
            self.load_image(self.current_image_index)
            self.current_image_index += 1
            self.update()
            # 如果想要控制處理速度，可以添加一點延遲，例如：self.after(1000)  # 暫停 1000 毫秒（1 秒）
        self.save_results_to_json()

    def stop_processing(self):
        self.processing = False

    def save_results_to_json(self):
        json_filename = os.path.basename(json_path)
        json_filename_without_extension = os.path.splitext(json_filename)[0]
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)
        output_filename = os.path.join(output_folder, f"{json_filename_without_extension}.json")

        with open(output_filename, "w") as json_file:
            json.dump(self.results, json_file, indent=2)
        print(f"Results saved to {output_filename}")

    def load_new_json(self):
        filepath = tk.filedialog.askopenfilename(
            title="Open JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filepath:
            with open(filepath, "r") as file:
                data = json.load(file)
                self.images = data['images']
                self.annotations = data['annotations']
                self.current_image_index = 0
                self.load_image(self.current_image_index)

    def process_all_jsons(self):
        # Directory containing the JSON files to be processed
        json_directory = "labels/labels_2d_pose_stitched_coco"
        # Directory where the processed files will be saved
        output_directory = "output"
        # Ensure the output directory exists
        os.makedirs(output_directory, exist_ok=True)

        # Iterate over each JSON file in the specified directory
        for json_file in glob.glob(os.path.join(json_directory, '*.json')):
            with open(json_file, 'r') as file:
                data = json.load(file)
                # Assign images and annotations from the current JSON file
                self.images = data['images']
                self.annotations = data['annotations']
                # Reset results for the current file
                self.results = []

                # Process each image in the current JSON file
                for i in range(len(self.images)):
                    self.current_image_index = i
                    self.load_image(i)
                    # The load_image method should update self.results with the processing outcome

                # Save the results to a corresponding JSON file in the output directory
                output_filename = os.path.join(output_directory, os.path.basename(json_file))
                with open(output_filename, 'w') as outfile:
                    json.dump(self.results, outfile, indent=2)
                print(f"Processed {json_file} and saved results to {output_filename}")

        print("All files processed.")

if __name__ == "__main__":
    json_path = "labels/labels_2d_pose_stitched_coco/cubberly-auditorium-2019-04-22_0.json"
    with open(json_path, "r") as file:
        data = json.load(file)

    viewer = ImageViewer(data['images'], data['annotations'])
    viewer.mainloop()

    # viewer.save_results_to_json()