import customtkinter as ctk
from PIL import Image



class GUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        button_color="darkblue"

        # General settings
        self.geometry("600x400")
        self.title("HandCtrl")
        self.resizable(False, False)

        # Frame
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Logo
        self.logo = ctk.CTkImage(light_image=Image.open("res/logo.png"), size=(50, 50))
        self.logo_label = ctk.CTkLabel(self.frame, image=self.logo, text="")
        self.logo_label.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Description
        self.description = ctk.CTkLabel(self.frame, text="Выберите функцию\n"
                                        "для продолжения работы",
                                        justify="left")
        self.description.grid(row=2, column=0, padx=10, pady=10)

        # Camera button
        self.open_camera_button = ctk.CTkButton(self.frame, fg_color=button_color, width=220, text="Открыть камеру", command=self.OpenCamera)
        self.open_camera_button.grid(row=3, column=1, padx=10, pady=5)

        # Update button
        self.update_button = ctk.CTkButton(self.frame, fg_color=button_color, width=220, text="Редактирование жестов", command=self.Update())
        self.update_button.grid(row=4, column=1, padx=10, pady=5)

        # Start button
        self.start_button = ctk.CTkButton(self.frame, fg_color=button_color, width=220, text="Запуск", command=self.Start())
        self.start_button.grid(row=5, column=1, padx=10, pady=5)

        # Quit button
        self.quit_button = ctk.CTkButton(self.frame, fg_color=button_color, text="Выход", command=self.Quit())
        self.quit_button.grid(row=6, column=2, padx=10, pady=5)

    def OpenCamera(self):
        print("opencamera")

    def Update(self):
        print("update")

    def Start(self):
        print("start")

    def Quit(self):
        print("quit")



if __name__ == "__main__":
    app = GUI()
    app.mainloop()
