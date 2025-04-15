import json
import os
import cv2
import threading
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image
from HandMouse import HandControl


class GUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Setup style for gui
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.button_color = "#1f538d"
        self.button_hover = "#14375e"
        self.danger_color = "#d34545"
        self.danger_hover = "#a83232"

        # Load config
        self.config_file = "config.json"
        self.config_data = self.load_config()

        # App status
        self.camera_running = False
        self.cap = None
        self._hand_control_running = False

        # Setup window
        self.geometry("1000x700")
        self.title("Hand Control")
        self.resizable(False, False)

        # Mainframe
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.show_main_menu()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        else:
            # Default config
            return {
                "settings": {
                    "smoothening": 7,
                    "frame_reduction": 0.1,
                    "adapter_for_cam": 50,
                    "click_delay": 20
                },
                "gestures": {
                    "right_hand": {
                        "move_mouse": {"fingers_up": [0, 1, 0, 0, 0]},
                        "left_one_click": {"fingers_up": [1, 1, 0, 0, 0]},
                        "left_double_click": {"fingers_up": [0, 1, 1, 0, 0]},
                        "right_click": {"fingers_up": [1, 1, 1, 0, 0], "distance_threshold": 40},
                        "scroll_up": {"fingers_up": [0, 1, 1, 1, 1]},
                        "scroll_down": {"fingers_up": [1, 0, 0, 0, 0]},
                        "hold_and_move": {"fingers_up": [0, 0, 0, 0, 0]},
                        "release": {"fingers_up": [1, 1, 1, 1, 1]}
                    },
                    "left_hand": {
                        "app_launch": {
                            "gestures": {
                                "nautilus": {
                                    "fingers_up": [0, 1, 0, 0, 0],
                                    "command": "nautilus"
                                },
                                "firefox": {
                                    "fingers_up": [0, 1, 1, 0, 0],
                                    "command": "firefox"
                                }
                            }
                        }
                    }
                }
            }

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=4, ensure_ascii=False)
            return True

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            return False

    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def create_header(self, title):
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(pady=(10, 20), padx=20, fill="x")

        # Logo and header
        if hasattr(self, 'logo'):
            logo_label = ctk.CTkLabel(header_frame, image=self.logo, text="")
            logo_label.pack(side="left", padx=(0, 15))

        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            title_frame,
            text=title,
            font=ctk.CTkFont(family="Arial", size=18, weight="bold"),
            anchor="w"
        ).pack(fill="x")

        # Return button
        back_button = ctk.CTkButton(
            header_frame,
            text="Назад",
            width=100,
            command=self.show_main_menu,
            fg_color=self.button_color,
            hover_color=self.button_hover
        )
        back_button.pack(side="right", padx=10)

        return header_frame

    def show_main_menu(self):

        self.clear_frame()

        # Stop all process
        if self.camera_running:
            self.stop_camera()
        if hasattr(self, '_hand_control_running'):
            self._hand_control_running = False

        # Main menu frame
        self.logo = ctk.CTkImage(light_image=Image.open("res/logo.png"), size=(70, 70))

        self.create_header("Главное меню")

        desc_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        desc_frame.pack(pady=(0, 20), padx=20, fill="x")

        ctk.CTkLabel(
            desc_frame,
            text="Выберите действие:",
            font=ctk.CTkFont(family="Arial", size=14),
            anchor="w"
        ).pack(fill="x")

        # Buttons menu
        buttons_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        buttons_frame.pack(pady=10, padx=20, expand=True)

        button_options = {
            "width": 200,
            "height": 50,
            "corner_radius": 10,
            "font": ctk.CTkFont(family="Arial", size=14, weight="bold"),
            "fg_color": self.button_color,
            "hover_color": self.button_hover
        }

        # Camera button
        ctk.CTkButton(
            buttons_frame,
            text="Просмотр камеры",
            command=self.open_camera,
            **button_options
        ).pack(pady=10, fill="x")

        # Update gestures button
        ctk.CTkButton(
            buttons_frame,
            text="Редактировать жесты",
            command=self.show_update_config,
            **button_options
        ).pack(pady=10, fill="x")

        # Start Hand Control button
        ctk.CTkButton(
            buttons_frame,
            text="Запустить управление",
            command=self.start_handcrtl,
            **button_options
        ).pack(pady=10, fill="x")

        # Exit button
        ctk.CTkButton(
            buttons_frame,
            text="Выход",
            command=self.exit,
            fg_color=self.danger_color,
            hover_color=self.danger_hover,
            **{k: v for k, v in button_options.items() if k not in ["fg_color", "hover_color"]}
        ).pack(pady=(30, 10), fill="x")

    def open_camera(self):
        self.clear_frame()
        self.create_header("Просмотр камеры")

        # Frame for cam
        self.camera_frame = ctk.CTkFrame(self.main_frame)
        self.camera_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.camera_label = ctk.CTkLabel(self.camera_frame, text="")
        self.camera_label.pack(fill="both", expand=True)

        # Start cam
        self.cap = cv2.VideoCapture(0)
        self.camera_running = True
        self.show_camera_feed()

    def show_camera_feed(self):
        if self.camera_running:
            ret, frame = self.cap.read()
            if ret:
                # Convert BGR -> RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Scaling
                h, w = frame.shape[:2]
                aspect_ratio = w / h
                new_height = 500
                new_width = int(new_height * aspect_ratio)
                frame = cv2.resize(frame, (new_width, new_height))

                # Sending video to frame
                img = Image.fromarray(frame)
                imgtk = ctk.CTkImage(light_image=img, size=(new_width, new_height))

                self.camera_label.configure(image=imgtk)
                self.camera_label.image = imgtk

            self.after(10, self.show_camera_feed)

    def stop_camera(self):
        if self.cap:
            self.cap.release()
        self.camera_running = False

    def show_update_config(self):
        self.clear_frame()
        self.create_header("Редактирование жестов")

        # Create tabs
        self.tabs = ctk.CTkTabview(self.main_frame)
        self.tabs.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Add tabs
        self.tabs.add("Общие настройки")
        self.tabs.add("Правая рука")
        self.tabs.add("Левая рука")

        # Tabs
        self.create_settings_tab()
        self.create_right_hand_tab()
        self.create_left_hand_tab()

        # Save button
        save_button = ctk.CTkButton(
            self.main_frame,
            text="Сохранить изменения",
            command=self.save_config_and_back,
            width=200,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(family="Arial", size=14, weight="bold"),
            fg_color=self.button_color,
            hover_color=self.button_hover
        )
        save_button.pack(pady=(10, 20))

    def save_config_and_back(self):
        if self.save_config():
            messagebox.showinfo("Успех", "Настройки успешно сохранены!")
            self.show_main_menu()

    def create_settings_tab(self):
        tab = self.tabs.tab("Общие настройки")

        # Create frame with scroll
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True)

        # Setting display
        settings = [
            ("Сглаживание", "smoothening", "int"),
            ("Уменьшение кадра", "frame_reduction", "float"),
            ("Адаптер камеры", "adapter_for_cam", "int"),
            ("Задержка клика", "click_delay", "int")
        ]

        for i, (label, key, var_type) in enumerate(settings):
            frame = ctk.CTkFrame(scroll_frame)
            frame.pack(fill="x", pady=5)

            ctk.CTkLabel(
                frame,
                text=label + ":",
                font=ctk.CTkFont(family="Arial", size=14)
            ).pack(side="left", padx=5)

            if var_type == "int":
                var = ctk.IntVar(value=self.config_data["settings"][key])
            else:
                var = ctk.DoubleVar(value=self.config_data["settings"][key])

            setattr(self, f"{key}_var", var)

            entry = ctk.CTkEntry(
                frame,
                textvariable=var,
                width=100,
                font=ctk.CTkFont(family="Arial", size=14)
            )
            entry.pack(side="right", padx=5)

    def create_right_hand_tab(self):
        # Create frame
        tab = self.tabs.tab("Правая рука")
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True)

        self.right_hand_vars = {}

        # Display gestures
        for gesture_name, gesture_data in self.config_data["gestures"]["right_hand"].items():
            self.create_gesture_controls(scroll_frame, "right_hand", gesture_name, gesture_data)

    def create_left_hand_tab(self):

        tab = self.tabs.tab("Левая рука")
        scroll_frame = ctk.CTkScrollableFrame(tab)
        scroll_frame.pack(fill="both", expand=True)

        self.left_hand_vars = {}

        # Frame for adding new gesture
        add_frame = ctk.CTkFrame(scroll_frame)
        add_frame.pack(fill="x", pady=(0, 20))

        # Add gesture button
        ctk.CTkButton(
            add_frame,
            text="+ Добавить жест",
            command=self.add_left_hand_gesture,
            width=150,
            height=30,
            fg_color=self.button_color,
            hover_color=self.button_hover
        ).pack(pady=5)

        # Display gestures
        for app_name, app_data in self.config_data["gestures"]["left_hand"]["app_launch"]["gestures"].items():
            gesture_frame = ctk.CTkFrame(scroll_frame)
            gesture_frame.pack(fill="x", pady=5)

            # Name gesture
            ctk.CTkLabel(
                gesture_frame,
                text=app_name + ":",
                font=ctk.CTkFont(family="Arial", size=14)
            ).pack(side="left", padx=5)

            fingers_frame = ctk.CTkFrame(gesture_frame)
            fingers_frame.pack(side="left", padx=10)

            fingers = ["Большой", "Указательный", "Средний", "Безымянный", "Мизинец"]
            finger_vars = []

            for i, finger in enumerate(fingers):
                finger_frame = ctk.CTkFrame(fingers_frame)
                finger_frame.pack(side="left", padx=2)

                ctk.CTkLabel(
                    finger_frame,
                    text=finger,
                    font=ctk.CTkFont(family="Arial", size=12)
                ).pack()

                var = ctk.IntVar(value=app_data["fingers_up"][i])
                cbox = ctk.CTkCheckBox(
                    finger_frame,
                    text="",
                    variable=var,
                    onvalue=1,
                    offvalue=0,
                    width=20
                )
                cbox.pack()
                finger_vars.append(var)

            # Поле команды
            cmd_frame = ctk.CTkFrame(gesture_frame)
            cmd_frame.pack(side="left", fill="x", expand=True, padx=10)

            ctk.CTkLabel(
                cmd_frame,
                text="Команда:",
                font=ctk.CTkFont(family="Arial", size=12)
            ).pack(anchor="w")

            cmd_var = ctk.StringVar(value=app_data["command"])
            cmd_entry = ctk.CTkEntry(
                cmd_frame,
                textvariable=cmd_var,
                font=ctk.CTkFont(family="Arial", size=12)
            )
            cmd_entry.pack(fill="x")

            # Сохраняем переменные
            self.left_hand_vars[app_name] = {
                "fingers": finger_vars,
                "command_var": cmd_var
            }

            # Delete button
            ctk.CTkButton(
                gesture_frame,
                text="Удалить",
                width=80,
                height=30,
                command=lambda name=app_name: self.remove_left_hand_gesture(name),
                fg_color=self.danger_color,
                hover_color=self.danger_hover
            ).pack(side="right", padx=5)

    def remove_left_hand_gesture(self, gesture_name):
        if messagebox.askyesno(
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить жест '{gesture_name}'?"
        ):
            del self.config_data["gestures"]["left_hand"]["app_launch"]["gestures"][gesture_name]

            if self.save_config():
                # Обновляем интерфейс
                self.show_update_config()
                messagebox.showinfo("Успех", f"Жест '{gesture_name}' успешно удалён")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить изменения")

    def add_left_hand_gesture(self):
        # Create frame for add gesture
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить жест")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self)

        # Display window
        def set_grab():
            if dialog.winfo_viewable():
                dialog.grab_set()
            else:
                dialog.after(100, set_grab)

        ctk.CTkLabel(
            dialog,
            text="Введите название приложения:",
            font=ctk.CTkFont(family="Arial", size=14)
        ).pack(pady=10)

        name_entry = ctk.CTkEntry(dialog, width=300)
        name_entry.pack(pady=5)

        ctk.CTkLabel(
            dialog,
            text="Введите команду для запуска:",
            font=ctk.CTkFont(family="Arial", size=14)
        ).pack(pady=10)

        cmd_entry = ctk.CTkEntry(dialog, width=300)
        cmd_entry.pack(pady=5)

        def save_gesture():
            app_name = name_entry.get().strip()
            command = cmd_entry.get().strip()

            if not app_name or not command:
                messagebox.showerror("Ошибка", "Название и команда не могут быть пустыми")
                return

            if app_name in self.config_data["gestures"]["left_hand"]["app_launch"]["gestures"]:
                messagebox.showerror("Ошибка", "Жест с таким именем уже существует")
                return

            self.config_data["gestures"]["left_hand"]["app_launch"]["gestures"][app_name] = {
                "fingers_up": [0, 0, 0, 0, 0],
                "command": command
            }

            dialog.grab_release()
            dialog.destroy()

            # Update frame
            self.show_update_config()

        save_button = ctk.CTkButton(
            dialog,
            text="Сохранить",
            command=save_gesture,
            fg_color=self.button_color,
            hover_color=self.button_hover
        )
        save_button.pack(pady=10)

        name_entry.focus_set()

        dialog.after(100, set_grab)

        def on_close():
            dialog.grab_release()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

    # Edit gestures for right hand
    def create_gesture_controls(self, parent, hand_type, gesture_name, gesture_data, is_app=False):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", pady=5)

        name_label = ctk.CTkLabel(
            frame,
            text=gesture_name.replace("_", " ").title() + ":",
            font=ctk.CTkFont(family="Arial", size=14)
        )
        name_label.pack(side="left", padx=5)

        fingers_frame = ctk.CTkFrame(frame)
        fingers_frame.pack(side="left", padx=10)

        fingers = ["Большой", "Указательный", "Средний", "Безымянный", "Мизинец"]
        finger_vars = []

        for i, finger in enumerate(fingers):
            finger_frame = ctk.CTkFrame(fingers_frame)
            finger_frame.pack(side="left", padx=2)

            ctk.CTkLabel(
                finger_frame,
                text=finger,
                font=ctk.CTkFont(family="Arial", size=12)
            ).pack()

            var = ctk.IntVar(value=gesture_data["fingers_up"][i])
            cbox = ctk.CTkCheckBox(
                finger_frame,
                text="",
                variable=var,
                onvalue=1,
                offvalue=0,
                width=20
            )
            cbox.pack()
            finger_vars.append(var)

        if is_app:
            cmd_frame = ctk.CTkFrame(frame)
            cmd_frame.pack(side="left", fill="x", expand=True, padx=10)

            ctk.CTkLabel(
                cmd_frame,
                text="Команда:",
                font=ctk.CTkFont(family="Arial", size=12)
            ).pack(anchor="w")

            cmd_var = ctk.StringVar(value=gesture_data["command"])
            cmd_entry = ctk.CTkEntry(
                cmd_frame,
                textvariable=cmd_var,
                font=ctk.CTkFont(family="Arial", size=12)
            )
            cmd_entry.pack(fill="x")

            self.left_hand_vars[gesture_name] = {
                "fingers": finger_vars,
                "command_var": cmd_var
            }

            ctk.CTkButton(
                frame,
                text="Удалить",
                width=80,
                height=30,
                command=lambda name=gesture_name: self.remove_gesture(name),
                fg_color=self.danger_color,
                hover_color=self.danger_hover
            ).pack(side="right", padx=5)
        else:
            self.right_hand_vars[gesture_name] = finger_vars

    def remove_gesture(self, gesture_name):
        if messagebox.askyesno("Подтверждение", f"Удалить жест '{gesture_name}'?"):
            del self.config_data["gestures"]["left_hand"]["app_launch"]["gestures"][gesture_name]
            self.show_update_config()

    def start_handcrtl(self):
        self.clear_frame()
        self.create_header("Управление мышью")

        # Frame for cam
        self.camera_frame = ctk.CTkFrame(self.main_frame)
        self.camera_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.camera_label = ctk.CTkLabel(self.camera_frame, text="")
        self.camera_label.pack(fill="both", expand=True)

        # Start app with threading
        def run_hand_control():
            w_cam, h_cam = 640, 360
            hand_control = HandControl(w_cam, h_cam)

            cap = cv2.VideoCapture(0)
            cap.set(3, w_cam)
            cap.set(4, h_cam)

            self._hand_control_running = True

            while hasattr(self, '_hand_control_running') and self._hand_control_running:
                ret, frame = cap.read()
                if not ret:
                    break

                frame = hand_control._process_frame(frame)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]
                aspect_ratio = w / h
                new_height = 500
                new_width = int(new_height * aspect_ratio)
                frame = cv2.resize(frame, (new_width, new_height))

                img = Image.fromarray(frame)
                imgtk = ctk.CTkImage(light_image=img, size=(new_width, new_height))

                self.camera_label.configure(image=imgtk)
                self.camera_label.image = imgtk

                self.update()

            cap.release()

        threading.Thread(target=run_hand_control, daemon=True).start()

    def exit(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти?"):
            self.destroy()


if __name__ == "__main__":
    app = GUI()
    app.mainloop()