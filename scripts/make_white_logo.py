with open('static/img/breakthru-logo.svg', 'r', encoding='utf-8') as f:
    svg = f.read()

svg_white = svg.replace('fill="#1F0961"', 'fill="#FFFFFF"')

with open('static/img/breakthru-logo-white.svg', 'w', encoding='utf-8') as f:
    f.write(svg_white)

print('Created static/img/breakthru-logo-white.svg')
