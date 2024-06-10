import math
import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import json
import os
import tkinter.filedialog
import glob


def head_orientation_estimation(keypoints, epsilon=1e-8, threshold=0.15, tolerance=500):
    # Define the keypoints
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    # Calculate vectors
    neck_to_head = (head[0] - neck[0], head[1] - neck[1])
    neck_to_right_eye = (right_eye[0] - neck[0], right_eye[1] - neck[1])
    neck_to_left_eye = (left_eye[0] - neck[0], left_eye[1] - neck[1])
    eye_to_eye = (left_eye[0] - right_eye[0], left_eye[1] - right_eye[1])

    # Calculate angles between vectors
    angle_neck_to_right_eye = math.atan2(neck_to_right_eye[1], neck_to_right_eye[0])
    angle_neck_to_left_eye = math.atan2(neck_to_left_eye[1], neck_to_left_eye[0])

    # Calculate the average angle
    angle_radians = (angle_neck_to_right_eye + angle_neck_to_left_eye) / 2

    # Calculate vertical distance between two eyes and head
    vertical_distance = abs(neck_to_head[1]) + epsilon

    # Calculate horizontal distance between eyes
    horizontal_distance = abs(eye_to_eye[0]) + epsilon

    # Convert the angle from radians to degrees
    angle_degrees = math.degrees(angle_radians)

    # Calculate the ratio of horizontal distance to vertical distance
    ratio = horizontal_distance / vertical_distance

    # Adjust angle based on the vertical distance
    angle_adjustment = 0.1 * vertical_distance  # You can adjust the multiplier as needed
    angle_degrees += angle_adjustment

    angle_degrees += 90

    if 15 >= angle_degrees >= -15:
        if 0.4 < ratio:
            if angle_degrees > 0:
                angle_degrees = 30
            else:
                angle_degrees = -30
        else:
            angle_degrees = 0
    elif -60 <= angle_degrees < -15:
        if ratio < 0.14:
            angle_degrees = -60
        else:
            angle_degrees = -30
    elif -70 <= angle_degrees < -60:
        if ratio < 0.07:
            angle_degrees = -90
        else:
            angle_degrees = -60
    elif -100 <= angle_degrees < -70:
        angle_degrees = -90
    elif 15 < angle_degrees <= 60:
        if ratio < 0.14:
            angle_degrees = 60
        else:
            angle_degrees = 30
    elif 60 < angle_degrees <= 70:
        if ratio < 0.06:
            angle_degrees = 90
        else:
            angle_degrees = 60
    elif 70 < angle_degrees <= 100:
        angle_degrees = 90
    else:
        angle_degrees = 180

    return angle_degrees


def head_orientation_classifier(keypoints, epsilon=1e-8, threshold=200, tolerance=500):
    math_result = head_orientation_estimation(keypoints, epsilon, threshold, tolerance)

    # Define the keypoints
    right_eye_v = keypoints[5] == 2
    left_eye_v = keypoints[8] == 2
    right_shoulder_v = keypoints[11] == 2
    left_shoulder_v = keypoints[17] == 2
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    if right_eye[1] <= 0 or left_eye[1] <= 0:
        return None

    # Double check hand visibility
    right_hand_x, right_hand_y, right_hand_v = keypoints[30], keypoints[31], keypoints[32]
    right_shoulder_x, right_shoulder_y = keypoints[15], keypoints[16]
    distance_right = ((right_hand_x - right_shoulder_x) ** 2 + (right_hand_y - right_shoulder_y) ** 2) ** 0.5
    if distance_right < threshold:
        right_shoulder_v = 2

    # Double check shoulder visibility
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
        if eyes_right:
            return math_result
        elif eyes_left:
            return math_result
        else:
            return 0
    elif right_eye_v and left_eye_v and right_shoulder_v:
        return math_result
    elif right_eye_v and left_eye_v and left_shoulder_v:
        return math_result
    elif right_eye_v and right_shoulder_v:
        if not left_shoulder_v:
            return 90
        else:
            return 90 if math_result >= 60 else 60
    elif left_eye_v and left_shoulder_v:
        if not right_shoulder_v:
            return -90
        else:
            return -90 if math_result <= -60 else -60
    elif not right_eye_v and not left_eye_v:
        if eyes_right:
            return 180 - math_result
        elif eyes_left:
            return -180 - math_result
        else:
            return 180
    elif right_shoulder_v:
        return 180 - math_result
    elif left_shoulder_v:
        return -180 - math_result
    else:
        return None  # In case none of the conditions are met


def head_orientation_optimizer(keypoints, epsilon=1e-8, threshold=200, tolerance=500):
    # Use the results from the trigonometric estimation and observability classifier
    trigonometric_result = head_orientation_estimation(keypoints, epsilon, threshold, tolerance)
    visibility_result = head_orientation_classifier(keypoints, epsilon, threshold, tolerance)

    if visibility_result is None:
        return trigonometric_result

    # Occlusion handling and weighted fusion
    head = (keypoints[0], keypoints[1])
    right_eye = (keypoints[3], keypoints[4])
    left_eye = (keypoints[6], keypoints[7])
    neck = (keypoints[12], keypoints[13])

    # Calculate additional parameters and constraints
    midpoint_x = (head[0] + neck[0]) / 2
    eyes_right = right_eye[0] >= midpoint_x and left_eye[0] >= midpoint_x
    eyes_left = right_eye[0] <= midpoint_x and left_eye[0] <= midpoint_x

    # Weighted fusion
    weights = {'trigonometric': 0.6, 'visibility': 0.4}
    if eyes_right or eyes_left:
        final_angle = weights['trigonometric'] * trigonometric_result + weights['visibility'] * visibility_result
    else:
        final_angle = trigonometric_result

    return final_angle


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
    def __init__(self, images, annotations, output_json_path="None"):
        super().__init__()

        self.images = images
        self.annotations = annotations
        self.current_image_index = 0
        self.results = []
        self.output_data = {}
        self.track_id_to_color = {}

        self.show_skeleton = True
        self.show_keypoints = True
        self.show_box = False
        self.display_output_info_flag = True
        self.output_json_path = output_json_path

        if output_json_path not in [None, "None"]:
            self.load_output_json(output_json_path)

        self.geometry(f"{self.winfo_screenwidth()}x1")
        self.create_widgets()
        self.bind_events()
        self.load_image(self.current_image_index)

    def create_widgets(self):
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.load_raw_json_button = tk.Button(self, text="Load JSON", command=self.load_raw_json)
        self.load_raw_json_button.pack(side=tk.LEFT)

        self.frame_entry = tk.Entry(self, width=10)
        self.frame_entry.pack(side=tk.LEFT)
        self.goto_button = tk.Button(self, text="Go to Frame", command=self.goto_frame)
        self.goto_button.pack(side=tk.LEFT)

        self.save_button = tk.Button(self, text="Process", command=self.process_frames)
        self.save_button.pack(side=tk.LEFT)

        self.track_id_label = tk.Label(self, text="Track ID:")
        self.track_id_label.pack(side=tk.LEFT)
        self.track_id_entry = tk.Entry(self, width=10)
        self.track_id_entry.pack(side=tk.LEFT)

        self.orientation_label = tk.Label(self, text="New Orientation:")
        self.orientation_label.pack(side=tk.LEFT)
        self.orientation_entry = tk.Entry(self, width=10)
        self.orientation_entry.pack(side=tk.LEFT)

        self.save_button = tk.Button(self, text="Save Orientation", command=self.save_orientation)
        self.save_button.pack(side=tk.LEFT)

        self.toggle_skeleton_button = tk.Button(self, text="Skeleton", command=self.toggle_skeleton)
        self.toggle_skeleton_button.pack(side=tk.LEFT)

        self.toggle_keypoints_button = tk.Button(self, text="Keypoints", command=self.toggle_keypoints)
        self.toggle_keypoints_button.pack(side=tk.LEFT)

        self.toggle_output_info_button = tk.Button(self, text="Info", command=self.toggle_output_info)
        self.toggle_output_info_button.pack(side=tk.LEFT)

        self.toggle_box_button = tk.Button(self, text="Box", command=self.toggle_box)
        self.toggle_box_button.pack(side=tk.LEFT)

    def bind_events(self):
        self.bind("<Left>", self.prev_image)
        self.bind("<Right>", self.next_image)

    def load_and_resize_image(self, image_path):
        with Image.open(image_path) as img:
            screen_width = self.winfo_screenwidth()
            scale_factor = screen_width / img.width
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)

            img = img.resize((new_width, new_height))
            self.tk_image = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

            control_panel_height = 50
            window_height = new_height + control_panel_height
            self.geometry(f"{new_width}x{window_height}")

            return img, scale_factor

    def draw_keypoints(self, keypoints, scale_factor):
        indices_to_draw = [1, 2, 3, 4, 5, 6, 7]
        for i in range(len(keypoints) // 3):
            if i in indices_to_draw:
                x, y, v = keypoints[i * 3], keypoints[i * 3 + 1], keypoints[i * 3 + 2]
                x *= scale_factor
                y *= scale_factor
                fill_color = 'white' if v == 2 else 'black'
                self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=fill_color)

    def draw_skeleton(self, keypoints, scale_factor, color):
        keypoint_pairs = [
            (0, 4), (1, 2), (3, 4), (5, 4), (4, 8), (3, 6), (6, 9), (5, 7), (7, 12)
        ]
        for start_idx, end_idx in keypoint_pairs:
            start_keypoint = keypoints[start_idx * 3:start_idx * 3 + 3]
            end_keypoint = keypoints[end_idx * 3:end_idx * 3 + 3]
            if start_keypoint[2] > 0 and end_keypoint[2] > 0:
                start_x, start_y, _ = start_keypoint
                end_x, end_y, _ = end_keypoint
                start_x *= scale_factor
                start_y *= scale_factor
                end_x *= scale_factor
                end_y *= scale_factor
                distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
                if distance <= 500:
                    self.canvas.create_line(start_x, start_y, end_x, end_y, fill=color, width=2)

    def draw_head_box(self, keypoints, scale_factor, track_id):
        head_index = 0
        right_eye_index = 1
        left_eye_index = 2
        neck_index = 4

        head = (keypoints[head_index * 3] * scale_factor, keypoints[head_index * 3 + 1] * scale_factor)
        right_eye = (keypoints[right_eye_index * 3] * scale_factor, keypoints[right_eye_index * 3 + 1] * scale_factor)
        left_eye = (keypoints[left_eye_index * 3] * scale_factor, keypoints[left_eye_index * 3 + 1] * scale_factor)
        neck = (keypoints[neck_index * 3] * scale_factor, keypoints[neck_index * 3 + 1] * scale_factor)

        upper_bound_y = max(head[1], right_eye[1], left_eye[1], neck[1])
        lower_bound_y = min(head[1], right_eye[1], left_eye[1], neck[1])

        head_box_size = 5
        head_box_min_x = min(head[0], right_eye[0], left_eye[0], neck[0]) - head_box_size
        head_box_max_x = max(head[0], right_eye[0], left_eye[0], neck[0]) + head_box_size

        head_box_min_y = upper_bound_y
        head_box_max_y = lower_bound_y * 0.9

        if self.show_box:
            self.canvas.create_rectangle(head_box_min_x, head_box_min_y, head_box_max_x, head_box_max_y,
                                         outline='black', width=3)
            self.canvas.create_rectangle(head_box_min_x, head_box_min_y, head_box_max_x, head_box_max_y,
                                         outline='white', width=1)
        return head_box_min_x, head_box_min_y, head_box_max_y

    def load_image(self, index):
        self.canvas.delete("all")
        img_path = "images/" + self.images[index]['file_name']
        img, scale_factor = self.load_and_resize_image(img_path)

        image_id = self.images[index]['id']
        print(f"===================================== Image ID: {image_id} =====================================")

        canvas_width = self.winfo_screenwidth()
        self.canvas.create_text(canvas_width // 2, 10, text=f"Image ID: {image_id}", font=('Arial', 12), anchor=tk.N,
                                fill="white")
        self.canvas.create_text(canvas_width // 2 + 1, 11, text=f"Image ID: {image_id}", font=('Arial', 12),
                                anchor=tk.N, fill="black")

        colors = ["salmon", "turquoise", "orange", "chartreuse", "orchid"]
        annotations_for_image = [ann for ann in self.annotations if ann['image_id'] == image_id]

        for annotation in annotations_for_image:
            keypoints = annotation['keypoints']
            track_id = annotation.get("track_id", "N/A")

            if track_id not in self.track_id_to_color:
                self.track_id_to_color[track_id] = colors[len(self.track_id_to_color) % len(colors)]

            color = self.track_id_to_color[track_id]

            if self.show_skeleton:
                self.draw_skeleton(keypoints, scale_factor, color)
            if self.show_keypoints:
                self.draw_keypoints(keypoints, scale_factor)

            cord_x, cord_y, cord_y_top = self.draw_head_box(keypoints, scale_factor, track_id)
            self.display_head_orientation(keypoints, cord_x, cord_y, cord_y_top, track_id)
            self.display_output_info(image_id, track_id, cord_x, cord_y)

        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def display_head_orientation(self, keypoints, cord_x, cord_y, cord_y_top, track_id):
        orientation = head_orientation_optimizer(keypoints)
        info_text = f"({orientation}°)"
        id_text = f"id:{track_id}"

        self.canvas.create_text(cord_x + 1, cord_y + 21, text=info_text, font=('Arial', 10), anchor=tk.NW, fill="black")
        self.canvas.create_text(cord_x, cord_y + 20, text=info_text, font=('Arial', 10), anchor=tk.NW, fill="white")

        self.canvas.create_text(cord_x + 1, cord_y_top - 10 + 1, text=id_text, font=('Arial', 8), anchor=tk.NW,
                                fill="black")
        self.canvas.create_text(cord_x, cord_y_top - 10, text=id_text, font=('Arial', 8), anchor=tk.NW, fill="white")

        result = {
            "image_id": self.current_image_index,
            "track_id": track_id,
            "orientation": orientation,
            "cord_y_top": cord_y_top
        }
        self.results.append(result)

        print(f"Track ID: {track_id}  Orientation: {orientation}°")

    def display_output_info(self, image_id, track_id, base_x, base_y):
        if not self.display_output_info_flag:
            return

        image_id = int(image_id) - 1
        track_id = int(track_id)

        output_info = next((item for item in self.output_data if
                            int(item["image_id"]) == image_id and int(item["track_id"]) == track_id), None)

        if output_info:
            orientation = output_info.get("orientation", "N/A")
            info_text = f"{orientation}° "
            vertical_offset = -10
            self.canvas.create_text(base_x + 1, base_y + vertical_offset + 1, text=info_text, font=('Arial', 10),
                                    anchor=tk.NW, fill="purple")
            self.canvas.create_text(base_x, base_y + vertical_offset, text=info_text, font=('Arial', 10), anchor=tk.NW,
                                    fill="yellow")
        else:
            print(f"No output info found for image_id {image_id}, track_id {track_id}")

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

    def next_image(self, event):
        if self.current_image_index < len(self.images) - 1:
            self.current_image_index += 1
            self.load_image(self.current_image_index)

    def prev_image(self, event):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image(self.current_image_index)

    def output_to_json(self):
        json_filename = os.path.basename(raw_json_path)
        json_filename_without_extension = os.path.splitext(json_filename)[0]
        output_folder = "output"
        os.makedirs(output_folder, exist_ok=True)
        output_filename = os.path.join(output_folder, f"{json_filename_without_extension}.json")

        with open(output_filename, "w") as json_file:
            json.dump(self.results, json_file, indent=2)
        print(f"Results saved to {output_filename}")

    def process_frames(self):
        while self.current_image_index < len(self.images):
            self.load_image(self.current_image_index)
            self.current_image_index += 1
            self.update()

    def stop_processing(self):
        self.processing = False

    def save_orientation(self):
        track_id = int(self.track_id_entry.get())
        new_orientation = int(self.orientation_entry.get())
        image_id = self.current_image_index

        updated = self.update_orientation(image_id, track_id, new_orientation)

        if updated:
            self.save_updated_output_json()
            self.load_image(self.current_image_index)

    def update_orientation(self, image_id, track_id, new_orientation):
        for item in self.output_data:
            if item["image_id"] == image_id and item["track_id"] == track_id:
                item["orientation"] = new_orientation
                print(f"Updated orientation for image_id {image_id}, track_id {track_id} to {new_orientation}")
                return True
        print("Track ID not found for the current image.")
        return False

    def save_updated_output_json(self):
        if self.output_json_path and os.path.isdir(os.path.dirname(self.output_json_path)):
            try:
                with open(self.output_json_path, 'w') as file:
                    json.dump(self.output_data, file, indent=4)
                print(f"Successfully saved updates to {self.output_json_path}.")
            except Exception as e:
                print(f"Failed to save updates: {e}")
        else:
            print("No output JSON file path specified or path is invalid.")

    def load_raw_json(self):
        filepath = filedialog.askopenfilename(title="Open JSON file",
                                              filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if filepath:
            with open(filepath, "r") as file:
                data = json.load(file)
                self.images = data['images']
                self.annotations = data['annotations']
                self.current_image_index = 0
                self.load_image(self.current_image_index)

            base_name = os.path.basename(filepath)
            self.output_json_path = os.path.join("output", base_name)

            if os.path.exists(self.output_json_path):
                self.load_output_json(self.output_json_path)
            else:
                print(f"Output JSON file not found: {self.output_json_path}")

            self.load_image(self.current_image_index)

    def load_output_json(self, output_json_path):
        try:
            with open(output_json_path, 'r') as file:
                self.output_data = json.load(file)
            print(f"Output data loaded successfully from {output_json_path}.")
        except FileNotFoundError:
            print(f"Output JSON file not found: {output_json_path}")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {output_json_path}")
        except Exception as e:
            print(f"Unexpected error loading {output_json_path}: {e}")

    def process_all_jsons(self):
        json_directory = "labels/labels_2d_pose_stitched_coco"
        output_directory = "output"
        os.makedirs(output_directory, exist_ok=True)

        for json_file in glob.glob(os.path.join(json_directory, '*.json')):
            with open(json_file, 'r') as file:
                data = json.load(file)
                self.images = data['images']
                self.annotations = data['annotations']
                self.results = []

                for i in range(len(self.images)):
                    self.current_image_index = i
                    self.load_image(i)

                output_filename = os.path.join(output_directory, os.path.basename(json_file))
                with open(output_filename, 'w') as outfile:
                    json.dump(self.results, outfile, indent=2)
                print(f"Processed {json_file} and saved results to {output_filename}")

        print("All files processed.")

    def toggle_skeleton(self):
        self.show_skeleton = not self.show_skeleton
        self.load_image(self.current_image_index)

    def toggle_keypoints(self):
        self.show_keypoints = not self.show_keypoints
        self.load_image(self.current_image_index)

    def toggle_box(self):
        self.show_box = not self.show_box
        self.load_image(self.current_image_index)

    def toggle_output_info(self):
        self.display_output_info_flag = not self.display_output_info_flag
        self.load_image(self.current_image_index)


if __name__ == "__main__":
    raw_json_path = "labels/labels_2d_pose_stitched_coco/bytes-cafe-2019-02-07_0.json"
    output_json_path = raw_json_path.replace("labels/labels_2d_pose_stitched_coco", "output")


    with open(raw_json_path, "r") as file:
        data = json.load(file)

    viewer = ImageViewer(data['images'], data['annotations'], output_json_path)
    viewer.mainloop()

    # viewer.output_json()