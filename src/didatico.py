"""
TP1 - BCC327 - Modo didático: demonstrações dos algoritmos de Computação Gráfica.

Rasterização de linhas (Bresenham):
    python src/didatico.py bresenham                    # 8 octantes + exemplo numérico
    python src/didatico.py bresenham --interativo       # clique para escolher os extremos
    python src/didatico.py bresenham --arvore data/dados_modelos2D/tree2D_Nterm008.vtk
    python src/didatico.py bresenham --arvore ARQ.vtk --vista frontal --tamanho 700
    python src/didatico.py bresenham --salvar figs/     # salva PNGs em vez de abrir janelas

Preenchimento de polígonos (Scanline Fill):
    python src/didatico.py poligonos                    # polígono côncavo + tabela por varredura
    python src/didatico.py poligonos --arvore data/dados_modelos2D/tree2D_Nterm008.vtk
    python src/didatico.py poligonos --salvar figs/

Aliasing e antialiasing (supersampling feito por nós):
    python src/didatico.py antialiasing                 # cena de teste (leque de retas)
    python src/didatico.py antialiasing --arvore data/dados_modelos2D/tree2D_Nterm008.vtk
    python src/didatico.py antialiasing --arvore ARQ.vtk --k 4 --ref 8 --salvar figs/

Recorte de segmentos (Cohen–Sutherland, Liang–Barsky, Cyrus–Beck):
    python src/didatico.py recorte                      # exemplo numérico + cena de teste
    python src/didatico.py recorte --arvore data/dados_modelos2D/tree2D_Nterm008.vtk
    python src/didatico.py recorte --arvore ARQ.vtk --janela 0.25 0.25 0.75 0.75 --salvar figs/
"""
import argparse
import os
import sys

import numpy as np

import modelo as md
import rasterizacao as R
import recorte as C
import transformacoes as T

# segmentos de teste: um por octante, partindo do centro de uma grade 23x23
CENTRO = (11, 11)
OCTANTES = [
    ((11, 11), (21, 14), "1º"), ((11, 11), (14, 21), "2º"),
    ((11, 11), (8, 21), "3º"), ((11, 11), (1, 14), "4º"),
    ((11, 11), (1, 8), "5º"), ((11, 11), (8, 1), "6º"),
    ((11, 11), (14, 1), "7º"), ((11, 11), (21, 8), "8º"),
]
EXEMPLO = ((2, 1), (13, 6))  # dx = 11, dy = 5 (primeiro octante)


# ---------------------------------------------------------------- utilitários
def _grade(ax, largura, altura):
    ax.set_xlim(-0.5, largura - 0.5)
    ax.set_ylim(altura - 0.5, -0.5)  # y para baixo, como em imagem
    ax.set_xticks(np.arange(-0.5, largura, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, altura, 1), minor=True)
    ax.grid(which="minor", color="#b8c0cc", linewidth=0.6)
    ax.tick_params(which="both", length=0)
    ax.set_xticks(range(0, largura, 2))
    ax.set_yticks(range(0, altura, 2))
    ax.set_aspect("equal")


def _pintar(ax, pixels, cor, alpha=1.0):
    from matplotlib.patches import Rectangle
    for x, y in pixels:
        ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=cor,
                               edgecolor="none", alpha=alpha))


def imprimir_tabela(p0, p1):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    print(f"\nExemplo numérico: ({x0},{y0}) -> ({x1},{y1})   "
          f"dx = {dx}, dy = {dy}, erro inicial = dx + dy = {dx + dy}")
    print(f"{'k':>3} {'x':>4} {'y':>4} {'erro':>6} {'2*erro':>7}  próximo passo")
    for k, x, y, e, e2, mov in R.tabela_passos(x0, y0, x1, y1):
        print(f"{k:>3} {x:>4} {y:>4} {e:>6} {e2:>7}  {mov}")
    n = len(R.bresenham(x0, y0, x1, y1))
    print(f"Total: {n} pixels (= max(|dx|,|dy|) + 1 = {max(abs(x1-x0), abs(y1-y0)) + 1})")


# ------------------------------------------------------------------- figuras
def fig_octantes():
    import matplotlib.pyplot as plt
    cores = plt.get_cmap("tab10").colors
    fig, ax = plt.subplots(figsize=(7, 7))
    for k, (p0, p1, nome) in enumerate(OCTANTES):
        pix = R.bresenham(*p0, *p1)
        _pintar(ax, pix, cores[k], 0.85)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color="black", lw=0.8)
        ax.text(p1[0], p1[1], f" {nome}", fontsize=9, va="center")
    _grade(ax, 23, 23)
    ax.set_title("Bresenham nos 8 octantes (linha preta = segmento ideal)")
    return fig


def fig_exemplo():
    import matplotlib.pyplot as plt
    (x0, y0), (x1, y1) = EXEMPLO
    passos = R.tabela_passos(x0, y0, x1, y1)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _pintar(ax, [(x, y) for _, x, y, *_ in passos], "#7fb2e5")
    ax.plot([x0, x1], [y0, y1], color="black", lw=1)
    for k, x, y, e, _, _ in passos:
        ax.text(x, y, f"{k}", ha="center", va="center", fontsize=9)
    _grade(ax, 16, 9)
    ax.set_title(f"Exemplo: ({x0},{y0}) → ({x1},{y1}). Número = ordem de geração do pixel")
    return fig


def demo_arvore(args):
    import matplotlib.pyplot as plt
    malha = md.carregar_modelo(args.arvore)
    nome_raio, onde = md.achar_raio(malha)
    if nome_raio is None:
        sys.exit("Não achei o atributo de raio no arquivo.")
    plano = abs(malha.bounds[5] - malha.bounds[4]) < 1e-12
    vista = args.vista or ("frontal" if plano else "isometrica")
    L = A = args.tamanho
    V, P = R.matrizes_ortograficas(malha, vista, L, A)
    M = np.eye(4)

    fb, seg_px, todos = R.rasterizar_modelo(malha, nome_raio, onde, M, V, P, L, A)
    _, _, todos_dda = R.rasterizar_modelo(malha, nome_raio, onde, M, V, P, L, A,
                                          algoritmo=R.dda)
    n_b = sum(len(p) for p in todos)
    n_d = sum(len(p) for p in todos_dda)
    difer = sum(len(set(a) ^ set(b)) for a, b in zip(todos, todos_dda))
    print(f"\nÁrvore rasterizada em {L}x{A} (vista {vista}, ortográfica)")
    print(f"  segmentos: {len(seg_px)} | pixels Bresenham: {n_b} | pixels DDA: {n_d}")
    print(f"  pixels que diferem entre os dois algoritmos: {difer}")

    # recorte de zoom em torno do meio do segmento mais longo
    comp = [max(abs(b[0] - a[0]), abs(b[1] - a[1])) for a, b in seg_px]
    k = int(np.argmax(comp))
    (ax0, ay0), (ax1, ay1) = seg_px[k]
    cx, cy = (ax0 + ax1) // 2, (ay0 + ay1) // 2
    r = 12
    xa, xb = max(cx - r, 0), min(cx + r, L)
    ya, yb = max(cy - r, 0), min(cy + r, A)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6),
                                 gridspec_kw={"width_ratios": [1.3, 1]})
    a1.imshow(fb, interpolation="nearest")
    a1.plot([xa, xb, xb, xa, xa], [ya, ya, yb, yb, ya], color="red", lw=1)
    a1.set_title(f"Árvore CCO rasterizada com Bresenham ({L}x{A})")
    a1.axis("off")
    a2.imshow(fb[ya:yb, xa:xb], interpolation="nearest",
              extent=(xa - 0.5, xb - 0.5, yb - 0.5, ya - 0.5))
    a2.plot([ax0, ax1], [ay0, ay1], color="black", lw=0.8)
    a2.set_xlim(xa - 0.5, xb - 0.5)
    a2.set_ylim(yb - 0.5, ya - 0.5)
    a2.set_xticks(np.arange(xa - 0.5, xb, 1), minor=True)
    a2.set_yticks(np.arange(ya - 0.5, yb, 1), minor=True)
    a2.grid(which="minor", color="#b8c0cc", linewidth=0.5)
    a2.tick_params(which="both", length=0)
    a2.set_title("Zoom (quadrado vermelho): pixels do segmento mais longo")
    fig.tight_layout()
    return fig


# -------------------------------------------------------------- interativo
class DemoInterativo:
    """Clique 1 define o início, clique 2 define o fim; o 3º recomeça."""

    def __init__(self, largura=40, altura=24):
        import matplotlib.pyplot as plt
        self.L, self.A = largura, altura
        self.pontos = []
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        _grade(self.ax, largura, altura)
        self.artistas = []
        self.fig.canvas.mpl_connect("button_press_event", self.clique)
        self._titulo("Clique para escolher o início do segmento")

    def _titulo(self, txt):
        self.ax.set_title(txt)
        self.fig.canvas.draw_idle()

    def clique(self, ev):
        if ev.inaxes is not self.ax or ev.xdata is None:
            return
        p = (int(round(ev.xdata)), int(round(ev.ydata)))
        if not (0 <= p[0] < self.L and 0 <= p[1] < self.A):
            return
        if len(self.pontos) != 1:      # 0 ou 2 pontos: recomeça
            for a in self.artistas:
                a.remove()
            self.artistas, self.pontos = [], [p]
            from matplotlib.patches import Rectangle
            r = Rectangle((p[0] - .5, p[1] - .5), 1, 1, facecolor="#e57373")
            self.ax.add_patch(r)
            self.artistas.append(r)
            self._titulo(f"Início em {p}. Clique para escolher o fim")
            return
        self.pontos.append(p)
        (x0, y0), (x1, y1) = self.pontos
        pix = R.bresenham(x0, y0, x1, y1)
        antes = len(self.ax.patches)
        _pintar(self.ax, pix, "#7fb2e5")
        self.artistas += self.ax.patches[antes:]
        (linha,) = self.ax.plot([x0, x1], [y0, y1], color="black", lw=1)
        self.artistas.append(linha)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        self._titulo(f"({x0},{y0}) → ({x1},{y1}): dx = {dx}, dy = {dy}, "
                     f"{len(pix)} pixels. Clique para recomeçar")


# ---------------------------------------------------------- scanline fill
# polígono côncavo de teste (entalhe em V no meio); tem aresta horizontal e
# um vértice em que duas arestas começam na mesma linha
POLIGONO = [(2, 1), (15, 1), (15, 11), (11, 6), (7, 11), (2, 11)]


def imprimir_tabela_scanline(vertices):
    print(f"\nScanline Fill — polígono {vertices}")
    et = R.tabela_arestas(vertices)
    print("Tabela de arestas (ET), sem as horizontais:")
    print(f"  {'y_min':>5} {'y_max':>5} {'x em y_min':>10} {'dx':>4} {'dy':>4}")
    for ymin, ymax, x0, dx, dy in et:
        print(f"  {ymin:>5} {ymax:>5} {x0:>10} {dx:>4} {dy:>4}")
    passos = []
    pix = R.scanline_fill(vertices, passos)
    print("\nVarredura (AET): interseções ordenadas e trechos preenchidos")
    print(f"  {'y':>3}  {'interseções x':<34} trechos [x_ini, x_fim]")
    for y, xs, trechos in passos:
        xs_txt = "  ".join(f"{x:6.2f}" for x in xs)
        tr = "  ".join(f"[{a}, {b}]" for a, b in trechos)
        print(f"  {y:>3}  {xs_txt:<34} {tr}")
    print(f"\nTotal: {len(pix)} pixels | área pela fórmula do cadarço: "
          f"{R.area_poligono(vertices):g}")


def fig_scanline_exemplo(vertices):
    import matplotlib.pyplot as plt
    passos = []
    pix = R.scanline_fill(vertices, passos)
    largura = max(x for x, _ in vertices) + 3
    altura = max(y for _, y in vertices) + 3
    fig, ax = plt.subplots(figsize=(8, 6.2))
    _pintar(ax, pix, "#7fb2e5")
    fx = [x for x, _ in vertices] + [vertices[0][0]]
    fy = [y for _, y in vertices] + [vertices[0][1]]
    ax.plot(fx, fy, color="black", lw=1.2, marker="o", ms=4)
    _grade(ax, largura, altura)
    ax.set_title("Scanline Fill em polígono côncavo (linha preta = contorno ideal)")
    return fig


def fig_scanline_roi(args):
    """Região de interesse (hexágono) preenchida sobre a árvore rasterizada."""
    import matplotlib.pyplot as plt
    malha = md.carregar_modelo(args.arvore)
    nome_raio, onde = md.achar_raio(malha)
    if nome_raio is None:
        sys.exit("Não achei o atributo de raio no arquivo.")
    plano = abs(malha.bounds[5] - malha.bounds[4]) < 1e-12
    vista = args.vista or ("frontal" if plano else "isometrica")
    L = A = args.tamanho
    V, P = R.matrizes_ortograficas(malha, vista, L, A)
    fb, _, _ = R.rasterizar_modelo(malha, nome_raio, onde, np.eye(4), V, P, L, A)

    cx, cy, r = L // 2, A // 2, int(0.28 * L)
    hexa = [(int(cx + r * np.cos(np.radians(a))), int(cy + r * np.sin(np.radians(a))))
            for a in range(0, 360, 60)]
    pix = R.scanline_fill(hexa)
    sobre = fb.copy().astype(float)
    cor = np.array([229, 115, 115], dtype=float)
    for x, y in pix:
        if 0 <= x < L and 0 <= y < A:
            sobre[y, x] = 0.65 * sobre[y, x] + 0.35 * cor
    # contorno com o nosso Bresenham
    for i in range(len(hexa)):
        p0, p1 = hexa[i], hexa[(i + 1) % len(hexa)]
        R.desenhar_pixels(sobre, R.bresenham(*p0, *p1), (200, 40, 40))
    print(f"\nRegião de interesse (hexágono) sobre a árvore {L}x{A}: "
          f"{len(pix)} pixels preenchidos (área ideal {R.area_poligono(hexa):g}).")

    fig, ax = plt.subplots(figsize=(7.5, 7.5))
    ax.imshow(sobre.astype(np.uint8), interpolation="nearest")
    ax.set_title("Região de interesse preenchida com Scanline Fill "
                 "(contorno: Bresenham)")
    ax.axis("off")
    return fig


# ---------------------------------------------------------- antialiasing
def cena_teste(L):
    """Leque de retas + uma reta quase horizontal: a escada fica bem visível
    (degraus longos nas retas de pouca inclinação)."""
    c = (L - 1) / 2
    r = 0.46 * L
    segs = [(c, c, c + r * np.cos(np.radians(a)), c + r * np.sin(np.radians(a)))
            for a in range(0, 360, 15)]
    segs.append((0.05 * L, 0.93 * L, 0.95 * L, 0.93 * L - 0.06 * L))
    segs = np.array(segs)
    return segs, [(20, 40, 100)] * len(segs)


def _nivel(img):
    return len(np.unique(img.reshape(-1, 3), axis=0))


def fig_aa_teste(k, L=64):
    import matplotlib.pyplot as plt
    segs, cores = cena_teste(L)
    sem = R.rasterizar_segmentos(segs, cores, L, L, k=1)
    com = R.rasterizar_segmentos(segs, cores, L, L, k=k)
    ref = R.rasterizar_segmentos(segs, cores, L, L, k=max(2 * k, 8))
    print(f"\nCena de teste {L}x{L}: EQM contra referência ({max(2 * k, 8)}x): "
          f"sem AA = {R.erro_medio_quadratico(sem, ref):.1f} | "
          f"SSAA {k}x{k} = {R.erro_medio_quadratico(com, ref):.1f}")
    print(f"  cores distintas: sem AA = {_nivel(sem)} | SSAA = {_nivel(com)}")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6.2))
    a1.imshow(sem, interpolation="nearest")
    a1.set_title("Sem antialiasing (Bresenham, 1 amostra por pixel)")
    a2.imshow(com, interpolation="nearest")
    a2.set_title(f"Supersampling {k}x{k} (média de {k * k} amostras por pixel)")
    for a in (a1, a2):
        a.axis("off")
    fig.tight_layout()
    return fig


def fig_aa_arvore(args):
    import matplotlib.pyplot as plt
    malha = md.carregar_modelo(args.arvore)
    nome_raio, onde = md.achar_raio(malha)
    if nome_raio is None:
        sys.exit("Não achei o atributo de raio no arquivo.")
    plano = abs(malha.bounds[5] - malha.bounds[4]) < 1e-12
    vista = args.vista or ("frontal" if plano else "isometrica")
    L = A = args.tamanho
    V, P = R.matrizes_ortograficas(malha, vista, L, A)
    segs, cores = R.segmentos_da_arvore(malha, nome_raio, onde, np.eye(4), V, P, L, A)

    k, kref = args.k, args.ref
    sem = R.rasterizar_segmentos(segs, cores, L, A, k=1)
    com = R.rasterizar_segmentos(segs, cores, L, A, k=k)
    ref = R.rasterizar_segmentos(segs, cores, L, A, k=kref)
    e0, e1 = R.erro_medio_quadratico(sem, ref), R.erro_medio_quadratico(com, ref)
    print(f"\nÁrvore {L}x{A} (vista {vista}): referência = supersampling {kref}x{kref}")
    print(f"  EQM sem AA      : {e0:8.2f}   cores distintas: {_nivel(sem)}")
    print(f"  EQM SSAA {k}x{k}   : {e1:8.2f}   cores distintas: {_nivel(com)}")
    print(f"  redução do erro : {100 * (1 - e1 / e0):.0f}%")

    comp = np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1])
    x0, y0, x1, y1 = segs[int(np.argmax(comp))]
    cx, cy, r = int((x0 + x1) / 2), int((y0 + y1) / 2), 14
    xa, xb = max(cx - r, 0), min(cx + r, L)
    ya, yb = max(cy - r, 0), min(cy + r, A)

    fig, ax = plt.subplots(2, 2, figsize=(11, 11))
    for a, img, tit in ((ax[0][0], sem, "Sem antialiasing"),
                        (ax[0][1], com, f"Supersampling {k}x{k}")):
        a.imshow(img, interpolation="nearest")
        a.plot([xa, xb, xb, xa, xa], [ya, ya, yb, yb, ya], color="red", lw=1)
        a.set_title(tit)
        a.axis("off")
    for a, img, tit in ((ax[1][0], sem, f"Zoom sem AA (EQM {e0:.1f})"),
                        (ax[1][1], com, f"Zoom SSAA {k}x{k} (EQM {e1:.1f})")):
        a.imshow(img[ya:yb, xa:xb], interpolation="nearest",
                 extent=(xa - 0.5, xb - 0.5, yb - 0.5, ya - 0.5))
        a.set_title(tit)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- recorte
CASOS = {
    "aceito": ("#2e7d32", "dentro (aceito direto)"),
    "recortado": ("#1565c0", "recortado"),
    "rejeitado": ("#c62828", "fora (rejeitado direto)"),
    "rejeitado_apos_recorte": ("#ef6c00", "fora (rejeitado após recortar)"),
}
EXEMPLO_RECORTE = ((0, 0), (12, 10), (2, 2, 10, 8))      # P0, P1, janela
JANELA_TESTE = (4, 3, 14, 9)
SEGMENTOS_TESTE = [
    (5, 8, 11, 8.5),     # dentro
    (1, 10, 5, 11.5),    # fora, mesmo lado (topo)
    (0, 6, 9, 5),        # cruza a esquerda
    (1, 11, 16, 2),      # cruza duas bordas (topo e direita)
    (0, 0, 18, 12),      # diagonal
    (12, 1, 17, 2),      # fora, mesmo lado (base)
    (8, 0, 8, 12),       # vertical, cruza base e topo
    (1, 8, 3, 2),        # fora, mesmo lado (esquerda)
    (3, 10, 8, 2),       # cruza o canto superior esquerdo
    (2, 8, 5, 10.5),     # passa fora do canto: só se sabe depois de recortar
]


def imprimir_exemplo_recorte():
    (x0, y0), (x1, y1), j = EXEMPLO_RECORTE
    xmin, ymin, xmax, ymax = j
    print(f"\nExemplo numérico: P0=({x0},{y0}) P1=({x1},{y1}), "
          f"janela x[{xmin},{xmax}] y[{ymin},{ymax}]")
    print("Códigos: ESQ=1 DIR=2 BAIXO=4 CIMA=8")
    print("\nCohen–Sutherland")
    print(f"  {'it':>2}  {'P0':<14}{'c0':>3}  {'P1':<14}{'c1':>3}  ação")
    for it, p0, c0, p1, c1, acao, novo in _passos_cs(x0, y0, x1, y1, j):
        extra = f" -> ({novo[0]:.2f}, {novo[1]:.2f})" if novo else ""
        print(f"  {it:>2}  ({p0[0]:.2f}, {p0[1]:.2f})".ljust(20)
              + f"{c0:>3}  ({p1[0]:.2f}, {p1[1]:.2f})".ljust(20)
              + f"{c1:>3}  {acao}{extra}")
    print("\nLiang–Barsky (u1 começa em 0 e u2 em 1)")
    print(f"  {'borda':<9}{'p':>5}{'q':>5}{'r=q/p':>9}{'u1':>8}{'u2':>8}  ação")
    passos = []
    res = C.liang_barsky(x0, y0, x1, y1, j, passos=passos)
    for nome, p, q, r, u1, u2, acao in passos:
        rt = f"{r:9.4f}" if r is not None else f"{'-':>9}"
        print(f"  {nome:<9}{p:>5}{q:>5}{rt}{u1:>8.4f}{u2:>8.4f}  {acao}")
    if res:
        print(f"  trecho visível: ({res[0]:.2f}, {res[1]:.2f}) -> ({res[2]:.2f}, {res[3]:.2f})")


def _passos_cs(x0, y0, x1, y1, j):
    passos = []
    C.cohen_sutherland(x0, y0, x1, y1, j, passos=passos)
    return passos


def classificar(segs, janela):
    """Recorta todos os segmentos com os 3 algoritmos. Devolve os resultados
    do Cohen–Sutherland, o caso de cada um e os contadores de operações."""
    res, casos = [], []
    cont_cs, cont_lb = {}, {}
    iguais = 0
    for s in segs:
        info = {}
        a = C.cohen_sutherland(*s, janela, cont=cont_cs, info=info)
        b = C.liang_barsky(*s, janela, cont=cont_lb)
        c = C.cyrus_beck(*s, C.janela_como_poligono(janela))
        iguais += C._iguais(a, b) and C._iguais(a, c)
        res.append(a)
        casos.append(info["caso"])
    return res, casos, cont_cs, cont_lb, iguais


def _janela_patch(ax, janela, **kw):
    from matplotlib.patches import Rectangle
    xmin, ymin, xmax, ymax = janela
    ax.add_patch(Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=False,
                           edgecolor="#6a1b9a", lw=1.6, ls="--", **kw))


def fig_recorte_teste():
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    segs = SEGMENTOS_TESTE
    res, casos, cs, lb, iguais = classificar(segs, JANELA_TESTE)
    print("\nCena de teste (janela x[4,14] y[3,9]):")
    for i, (s, r, c) in enumerate(zip(segs, res, casos)):
        trecho = ("-" if r is None else
                  f"({r[0]:.2f}, {r[1]:.2f}) -> ({r[2]:.2f}, {r[3]:.2f})")
        print(f"  {i}: {str(s):<24} {CASOS[c][1]:<32} {trecho}")
    print(f"  CS = LB = Cyrus–Beck em {iguais} de {len(segs)} segmentos")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.2), sharex=True, sharey=True)
    for i, (s, r, c) in enumerate(zip(segs, res, casos)):
        cor = CASOS[c][0]
        a1.plot([s[0], s[2]], [s[1], s[3]], color=cor, lw=2)
        a1.text(s[0], s[1], str(i), fontsize=8, color=cor)
        a2.plot([s[0], s[2]], [s[1], s[3]], color="#b0b0b0", lw=1, ls=":")
        if r is not None:
            a2.plot([r[0], r[2]], [r[1], r[3]], color=cor, lw=3,
                    solid_capstyle="round")
    for a, tit in ((a1, "Antes do recorte (cor = caso do Cohen–Sutherland)"),
                   (a2, "Depois do recorte (cinza pontilhado = parte descartada)")):
        _janela_patch(a, JANELA_TESTE)
        a.set_xlim(-1, 19)
        a.set_ylim(-1, 13)
        a.set_aspect("equal")
        a.set_title(tit, fontsize=10)
        a.grid(alpha=0.25)
    a1.legend(handles=[Line2D([0], [0], color=v[0], lw=2, label=v[1])
                       for v in CASOS.values()], fontsize=8, loc="upper right")
    fig.tight_layout()
    return fig


def fig_recorte_arvore(args):
    import matplotlib.pyplot as plt
    malha = md.carregar_modelo(args.arvore)
    nome_raio, onde = md.achar_raio(malha)
    if nome_raio is None:
        sys.exit("Não achei o atributo de raio no arquivo.")
    plano = abs(malha.bounds[5] - malha.bounds[4]) < 1e-12
    vista = args.vista or ("frontal" if plano else "isometrica")
    L = A = args.tamanho
    V, P = R.matrizes_ortograficas(malha, vista, L, A)
    segs, cores = R.segmentos_da_arvore(malha, nome_raio, onde, np.eye(4), V, P, L, A)
    fx0, fy0, fx1, fy1 = args.janela
    janela = (fx0 * L, fy0 * A, fx1 * L, fy1 * A)

    res, casos, cs, lb, iguais = classificar(segs.tolist(), janela)
    n = {k: casos.count(k) for k in CASOS}
    print(f"\nÁrvore {L}x{A} (vista {vista}), janela de recorte "
          f"x[{janela[0]:.0f}, {janela[2]:.0f}] y[{janela[1]:.0f}, {janela[3]:.0f}]")
    for k, (_, nome) in CASOS.items():
        print(f"  {nome:<34}: {n[k]}")
    print(f"  Cohen–Sutherland: {cs.get('intersecoes', 0)} interseções calculadas | "
          f"Liang–Barsky: {lb.get('divisoes', 0)} divisões")
    print(f"  resultados idênticos nos 3 algoritmos: {iguais} de {len(segs)}")

    vis = [(r, c) for r, c in zip(res, cores) if r is not None]
    fb = R.rasterizar_segmentos(np.array([r for r, _ in vis]).reshape(-1, 4),
                                [c for _, c in vis], L, A, k=1)

    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(17, 6))
    for s, r, c in zip(segs, res, cores / 255):
        a1.plot([s[0], s[2]], [s[1], s[3]], color=c, lw=1.2)
        a2.plot([s[0], s[2]], [s[1], s[3]], color="#c8c8c8", lw=0.8, ls=":")
        if r is not None:
            a2.plot([r[0], r[2]], [r[1], r[3]], color=c, lw=2)
    for a, tit in ((a1, "Antes do recorte"),
                   (a2, "Depois (Cohen–Sutherland; cinza = descartado)")):
        _janela_patch(a, janela)
        a.set_xlim(0, L)
        a.set_ylim(A, 0)
        a.set_aspect("equal")
        a.set_title(tit)
        a.axis("off")
    a3.imshow(fb, interpolation="nearest")
    _janela_patch(a3, janela)
    a3.set_title("Depois, rasterizado com Bresenham")
    a3.axis("off")
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="demo", required=True)

    b = sub.add_parser("bresenham", help="rasterização de linhas")
    b.add_argument("--interativo", action="store_true")
    p = sub.add_parser("poligonos", help="preenchimento de polígonos (Scanline Fill)")
    q = sub.add_parser("antialiasing", help="aliasing x supersampling")
    r = sub.add_parser("recorte", help="recorte de segmentos de reta")
    r.add_argument("--arvore", default=None, metavar="ARQ.vtk")
    r.add_argument("--vista", choices=list(T.VISTAS), default=None)
    r.add_argument("--tamanho", type=int, default=300)
    r.add_argument("--janela", type=float, nargs=4, default=[0.30, 0.30, 0.70, 0.70],
                   metavar=("X0", "Y0", "X1", "Y1"),
                   help="janela de recorte, em frações da imagem (0 a 1)")
    r.add_argument("--salvar", default=None, metavar="PASTA")
    q.add_argument("--k", type=int, default=4, help="fator de supersampling (k x k amostras)")
    q.add_argument("--ref", type=int, default=8, help="fator da imagem de referência")
    for sp in (b, p):
        sp.add_argument("--arvore", default=None, metavar="ARQ.vtk",
                        help="usa a árvore CCO (projeção ortográfica)")
        sp.add_argument("--vista", choices=list(T.VISTAS), default=None)
        sp.add_argument("--tamanho", type=int, default=600, help="lado da imagem, em pixels")
        sp.add_argument("--salvar", default=None, metavar="PASTA",
                        help="salva PNGs em vez de abrir janelas")
    q.add_argument("--arvore", default=None, metavar="ARQ.vtk")
    q.add_argument("--vista", choices=list(T.VISTAS), default=None)
    q.add_argument("--tamanho", type=int, default=300)
    q.add_argument("--salvar", default=None, metavar="PASTA")
    args = ap.parse_args()

    import matplotlib
    if args.salvar:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if args.demo == "bresenham":
        if args.interativo:
            demo = DemoInterativo()  # noqa: F841 (precisa ficar referenciado)
            plt.show()
            return
        imprimir_tabela(*EXEMPLO)
        figuras = {"bresenham_octantes": fig_octantes(), "bresenham_exemplo": fig_exemplo()}
        if args.arvore:
            figuras["bresenham_arvore"] = demo_arvore(args)
    elif args.demo == "recorte":
        imprimir_exemplo_recorte()
        figuras = {"recorte_teste": fig_recorte_teste()}
        if args.arvore:
            figuras["recorte_arvore"] = fig_recorte_arvore(args)
    elif args.demo == "antialiasing":
        figuras = {"antialiasing_teste": fig_aa_teste(args.k)}
        if args.arvore:
            figuras["antialiasing_arvore"] = fig_aa_arvore(args)
    else:
        imprimir_tabela_scanline(POLIGONO)
        figuras = {"scanline_exemplo": fig_scanline_exemplo(POLIGONO)}
        if args.arvore:
            figuras["scanline_roi"] = fig_scanline_roi(args)

    if args.salvar:
        os.makedirs(args.salvar, exist_ok=True)
        for nome, fig in figuras.items():
            arq = os.path.join(args.salvar, nome + ".png")
            fig.savefig(arq, dpi=150, bbox_inches="tight")
            print("salvo:", arq)
    else:
        plt.show()


if __name__ == "__main__":
    main()