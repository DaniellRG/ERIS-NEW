"""DearPyGui dark theme setup."""
import dearpygui.dearpygui as dpg


def setup_theme():
    with dpg.theme() as theme_global:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (15, 15, 25))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (20, 20, 35))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, (22, 22, 38))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (50, 50, 80))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (28, 28, 48))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (40, 40, 65))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (50, 50, 75))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (12, 12, 22))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (12, 12, 22))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, (15, 15, 25))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, (50, 50, 80))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (70, 70, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (90, 90, 120))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (30, 30, 55))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (50, 50, 80))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (60, 60, 95))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (35, 35, 60))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (50, 50, 80))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (60, 60, 95))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (50, 50, 80))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (220, 220, 240))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, (100, 100, 120))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
    dpg.bind_theme(theme_global)
