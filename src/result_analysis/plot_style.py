import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

font_path = '~/.fonts/CrimsonPro/CrimsonPro-VariableFont_wght.ttf'
fm.fontManager.addfont(font_path)
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rcParams['font.family'] = font_name

FONTS = {
    'font.family': 'serif',
    'font.serif': ['Crimson Pro'],
    'mathtext.fontset': 'custom',
    'mathtext.rm': 'Crimson Pro',
    'mathtext.bf': 'Crimson Pro:bold',
    'mathtext.it': 'Crimson Pro:italic',
    'font.size': 14,
}

COLOR_PALLETTE = {
    'blue': '#0072B2',
    'orange': '#D55E00',
    'green': '#009E73',
    'yellow': '#E69F00',
}
