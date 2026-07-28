import tkinter as tk
import threading

class VisualExpressionsInterface:
    def __init__(self):
        self.root = None
        self.canvas = None
        self.expression = "neutral"
        self.running = False
        self.face_elements = {}

    def show(self):
        if self.running:
            return

        def run():
            self.running = True
            self.root = tk.Tk()
            self.root.title("Eris Visual Expressions")
            self.root.geometry("400x400")
            
            self.root.update_idletasks()
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = (self.root.winfo_screenwidth() // 2) - (width // 2)
            y = (self.root.winfo_screenheight() // 2) - (height // 2)
            self.root.geometry(f'+{x}+{y}')

            self.canvas = tk.Canvas(self.root, width=400, height=400, bg='white')
            self.canvas.pack()
            self.draw_face()
            self.update_expression(self.expression)
            
            def on_close():
                self.running = False
                self.root.destroy()

            self.root.protocol("WM_DELETE_WINDOW", on_close)
            self.root.mainloop()

        threading.Thread(target=run).start()
        return "Interfaz visual de expresiones iniciada."

    def draw_face(self):
        self.canvas.delete("all")
        # Head
        self.face_elements['head'] = self.canvas.create_oval(100, 100, 300, 300, fill='yellow', outline='black')
        # Eyes
        self.face_elements['left_eye'] = self.canvas.create_oval(150, 160, 180, 190, fill='black')
        self.face_elements['right_eye'] = self.canvas.create_oval(220, 160, 250, 190, fill='black')
        # Mouth placeholder
        self.face_elements['mouth'] = self.canvas.create_line(150, 250, 250, 250, fill='black', width=3)

    def update_expression(self, expression):
        if self.running and self.canvas:
            self.expression = expression
            self.canvas.delete(self.face_elements['mouth'])
            
            if expression == "happy":
                self.face_elements['mouth'] = self.canvas.create_arc(150, 230, 250, 270, start=0, extent=-180, fill='black', style=tk.ARC, width=3)
            elif expression == "sad":
                self.face_elements['mouth'] = self.canvas.create_arc(150, 250, 250, 290, start=0, extent=180, fill='black', style=tk.ARC, width=3)
            elif expression == "surprised":
                self.face_elements['mouth'] = self.canvas.create_oval(185, 235, 215, 265, fill='black')
            else: # neutral
                self.face_elements['mouth'] = self.canvas.create_line(150, 250, 250, 250, fill='black', width=3)
            return f"Expresión visual actualizada a: {expression}"
        return "La interfaz visual no está corriendo."

visual_expressions_interface = VisualExpressionsInterface()

def visual_expressions(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action")
    expression = parameters.get("expression", "neutral")

    if action == "show":
        return visual_expressions_interface.show()
    elif action == "update":
        return visual_expressions_interface.update_expression(expression)
    elif action == "hide":
        return visual_expressions_interface.hide()
    return "Acción no válida."