import tkinter as tk

class Calculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculadora Eris")
        self.root.geometry("350x450")
        
        self.equation = tk.StringVar()
        self.entry = tk.Entry(root, textvariable=self.equation, font=('Arial', 24), bd=10, insertwidth=4, justify='right')
        self.entry.grid(row=0, column=0, columnspan=4)

        self.create_buttons()

    def create_buttons(self):
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            'C', '0', '=', '+'
        ]
        row, col = 1, 0
        for button in buttons:
            tk.Button(self.root, text=button, padx=5, pady=5, font=('Arial', 12),
                      command=lambda b=button: self.on_button_click(b)).grid(row=row, column=col, sticky="nsew")
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        for i in range(4):
            self.root.grid_columnconfigure(i, weight=1)
        for i in range(1, 5):
            self.root.grid_rowconfigure(i, weight=1)

    def on_button_click(self, button):
        if button == 'C':
            self.equation.set("")
        elif button == '=':
            try:
                expression = self.equation.get()
                # Basic security check for eval
                if any(char in expression for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'):
                     self.equation.set("Error")
                     return
                result = str(eval(expression))
                self.equation.set(result)
            except Exception:
                self.equation.set("Error")
        else:
            self.equation.set(self.equation.get() + str(button))

if __name__ == "__main__":
    root = tk.Tk()
    app = Calculator(root)
    root.mainloop()
