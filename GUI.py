import customtkinter as ctk
from PIL import Image



class GUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.geometry("460x370")
        self.title("HandCTRL")
        self.resizable(False, False)

        self.logo = ctk.CTkImage(Image.open("res/logo.png"), size=(50, 50))
        self.logo_label = ctk.CTkLabel(master=self, text='', image=self.logo)
        self.logo_label.grid(row=0, column=0)

        # Frames
        self.main_frame = ctk.CTkFrame(master=self, fg_color="transparent")
        self.main_frame.grid(row=1, column=0, padx=(20, 20), sticky="nsew")

        self.entry_main = ctk.CTkEntry(master=self.main_frame, width=300)
        self



if __name__ == "__main__":
    app = GUI()
    app.mainloop()