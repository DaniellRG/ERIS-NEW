using System;

namespace Calculadora
{
    class Program
    {
        static void Main(string[] args)
        {
            bool continuar = true;
            while (continuar)
            {
                MostrarMenu();
                int opcion = LeerOpcion();

                if (opcion == 5)
                {
                    continuar = false;
                    Console.WriteLine("Gracias por usar la calculadora.");
                    continue;
                }

                Console.Write("Ingrese primer número: ");
                double num1 = ConvertirADouble();
                Console.Write("Ingrese segundo número: ");
                double num2 = ConvertirADouble();

                double resultado = 0;
                try
                {
                    switch (opcion)
                    {
                        case 1:
                            resultado = Sumar(num1, num2);
                            break;
                        case 2:
                            resultado = Restar(num1, num2);
                            break;
                        case 3:
                            resultado = Multiplicar(num1, num2);
                            break;
                        case 4:
                            resultado = Dividir(num1, num2);
                            break;
                        case 5:
                            // Ya manejado anteriormente
                            break;
                        default:
                            Console.WriteLine("Opción inválida.");
                            continue;
                    }
                }
                catch (DivideByZeroException)
                {
                    Console.WriteLine("Error: No se puede dividir por cero.");
                    continue;
                }

                Console.WriteLine($"Resultado: {resultado}");
                Console.WriteLine("Presione cualquier tecla para continuar...");
                Console.ReadKey();
            }
        }

        static void MostrarMenu()
        {
            Console.Clear();
            Console.WriteLine("=== Calculadora ===");
            Console.WriteLine("1. Sumar");
            Console.WriteLine("2. Restar");
            Console.WriteLine("3. Multiplicar");
            Console.WriteLine("4. Dividir");
            Console.WriteLine("5. Salir");
            Console.Write("Seleccione una opción: ");
        }

        static int LeerOpcion()
        {
            while (true)
            {
                if (int.TryParse(Console.ReadLine(), out int opcion) && opcion >= 1 && opcion <= 5)
                    return opcion;
                Console.WriteLine("Opción inválida. Intente nuevamente.");
            }
        }

        static double ConvertirADouble()
        {
            while (true)
            {
                if (double.TryParse(Console.ReadLine(), out double valor))
                    return valor;
                Console.WriteLine("Número inválido. Intente nuevamente.");
            }
        }

        static double Sumar(double a, double b) => a + b;
        static double Restar(double a, double b) => a - b;
        static double Multiplicar(double a, double b) => a * b;
        static double Dividir(double a, double b)
        {
            if (b == 0) throw new DivideByZeroException();
            return a / b;
        }
    }
}