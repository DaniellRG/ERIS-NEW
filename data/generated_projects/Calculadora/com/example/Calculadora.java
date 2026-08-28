package com.example;

import java.util.Scanner;

public class Calculadora {
 
    private static final String MENU_SUMA = "1. Suma";
    private static final String MENU_RESTA = "2. Resta";
    private static final String MENU_MULTIPLICACION = "3. Multiplicación";
    private static final String MENU_DIVISION = "4. División";
    private static final String MENU_SALIR = "5. Salir";

    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        boolean continuar = true;
        
        while (continuar) {
            mostrarMenu();
            int opcion = leerOpcion(scanner);
            
            if (opcion == 5) {
                continuar = false;
                System.out.println("Gracias por usar la calculadora.");
                continue;
            }
            
            try {
                double numero1 = leerNumero(scanner, "Ingrese el primer número:");
                double numero2 = leerNumero(scanner, "Ingrese el segundo número:");
                double resultado = realizarOperacion(opcion, numero1, numero2);
                System.out.println("Resultado: " + resultado);
            } catch (ArithmeticException e) {
                System.out.println("Error: No se puede dividir por cero.");
            } catch (NumberFormatException e) {
                System.out.println("Error: Ingrese un número válido.");
            }
            
            System.out.print("¿Desea realizar otra operación? (s/n): ");
            continuar = scanner.nextLine().toLowerCase().startsWith("s");
        }
        
        scanner.close();
    }

    private static void mostrarMenu() {
        System.out.println("\n=== Menú de Operaciones ===");
        System.out.println(MENU_SUMA);
        System.out.println(MENU_RESTA);
        System.out.println(MENU_MULTIPLICACION);
        System.out.println(MENU_DIVISION);
        System.out.println(MENU_SALIR);
        System.out.print("Seleccione una opción: ");
    }

    private static int leerOpcion(Scanner scanner) {
        while (true) {
            String input = scanner.nextLine();
            if (input.matches("[1-5]")) {
                return Integer.parseInt(input);
            }
            System.out.print("Opción inválida. Intente nuevamente: ");
        }
    }

    private static double leerNumero(Scanner scanner, String mensaje) {
        while (true) {
            System.out.print(mensaje + " ");
            String input = scanner.nextLine();
            if (input.matches("-?[0-9]+([.][0-9]+)?")) {
                return Double.parseDouble(input);
            }
            System.out.println("Entrada inválida. Por favor ingrese un número.");
        }
    }

    private static double realizarOperacion(int opcion, double a, double b) {
        switch (opcion) {
            case 1: return a + b;
            case 2: return a - b;
            case 3: return a * b;
            case 4:
            if (b == 0) {
                System.out.println("Error: No se puede dividir por cero.");
                return 0.0;
            }
            return a / b;
            default: throw new IllegalArgumentException("Opción inválida");
        }
    }
}