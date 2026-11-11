"""
TP1 - BCC327 - Rasterização de linhas.

Tudo aqui é nosso (numpy/Python puro, sem VTK nem OpenGL):
  - bresenham: algoritmo de Bresenham em aritmética inteira, nos 8 octantes
  - dda: algoritmo DDA (ponto flutuante), só para comparação
  - framebuffer e rasterização do modelo CCO projetado em 2D

Convenção de pixels: (x, y) inteiros, x cresce para a direita e y para BAIXO
(como numa imagem). O centro do pixel (i, j) fica nas coordenadas (i, j).
"""
import numpy as np

import modelo as md
import transformacoes as T


# ------------------------------------------------------------ Bresenham
def bresenham_passos(x0, y0, x1, y1):
    """Gera (x, y, erro) para cada pixel do segmento, do início ao fim.

    Ideia: o 'erro' mede o quanto a linha ideal está distante do pixel
    escolhido, sem usar divisão nem ponto flutuante.
        dx = |x1 - x0|,  dy = -|y1 - y0|,  erro inicial = dx + dy
    A cada pixel, com e2 = 2*erro:
        e2 >= dy  -> o erro permite avançar em x   (erro += dy, x += sx)
        e2 <= dx  -> o erro permite avançar em y   (erro += dx, y += sy)
    É a mesma decisão do parâmetro p = 2*dy - dx do primeiro octante
    (0 <= m <= 1), só que escrita de forma simétrica para funcionar nos 8
    octantes sem precisar trocar eixos. Retas horizontais, verticais,
    diagonais e pontos (início = fim) caem como casos particulares.
    """
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    erro = dx + dy
    x, y = x0, y0
    while True:
        yield x, y, erro
        if x == x1 and y == y1:
            break
        e2 = 2 * erro
        if e2 >= dy:
            erro += dy
            x += sx
        if e2 <= dx:
            erro += dx
            y += sy


def bresenham(x0, y0, x1, y1):
    """Lista de pixels (x, y) do segmento."""
    return [(x, y) for x, y, _ in bresenham_passos(x0, y0, x1, y1)]


def tabela_passos(x0, y0, x1, y1):
    """Linhas da tabela passo a passo (para o relatório):
    (k, x, y, erro, e2, movimento)."""
    passos = list(bresenham_passos(x0, y0, x1, y1))
    linhas = []
    for k, (x, y, erro) in enumerate(passos):
        if k + 1 < len(passos):
            nx, ny, _ = passos[k + 1]
            mov = {(1, 0): "x", (0, 1): "y", (1, 1): "x e y"}.get(
                (abs(nx - x), abs(ny - y)), "x e y")
        else:
            mov = "fim"
        linhas.append((k, x, y, erro, 2 * erro, mov))
    return linhas


# ------------------------------------------------------------------ DDA
def dda(x0, y0, x1, y1):
    """DDA: avança 1 pixel no eixo de maior variação e soma o incremento
    (em ponto flutuante) no outro eixo, arredondando a cada passo."""
    dx, dy = x1 - x0, y1 - y0
    n = max(abs(dx), abs(dy))
    if n == 0:
        return [(x0, y0)]
    xi, yi = dx / n, dy / n
    return [(int(np.floor(x0 + i * xi + 0.5)), int(np.floor(y0 + i * yi + 0.5)))
            for i in range(n + 1)]


# ----------------------------------------------------------- framebuffer
def novo_framebuffer(largura, altura, cor=(255, 255, 255)):
    return np.full((altura, largura, 3), cor, dtype=np.uint8)


def desenhar_pixels(fb, pixels, cor):
    """Pinta pixels, ignorando os que caem fora da imagem. (Recorte de
    verdade, geométrico, é o assunto do Módulo 6.)"""
    altura, largura = fb.shape[:2]
    for x, y in pixels:
        if 0 <= x < largura and 0 <= y < altura:
            fb[y, x] = cor


def para_pixels(pontos, V, P, largura, altura):
    """Pontos do mundo (N,3) -> pixels inteiros (N,2).
    Usa as nossas matrizes (transformacoes.py) e a transformação de
    viewport: NDC [-1,1] -> [0, largura-1] x [0, altura-1], com y invertido."""
    ndc = T.projetar(pontos, V, P)
    x = (ndc[:, 0] + 1) / 2 * (largura - 1)
    y = (1 - ndc[:, 1]) / 2 * (altura - 1)
    return np.rint(np.c_[x, y]).astype(int)


def matrizes_ortograficas(malha, vista, largura, altura):
    """V e P ortográficas que enquadram o modelo inteiro na imagem."""
    centro = np.array(malha.center)
    diag = malha.length
    dist = 2.8 * diag
    V = T.olhar_para(*T.camera_da_vista(vista, centro, dist))
    h = 0.6 * diag
    a = largura / altura
    P = T.ortografica(-h * a, h * a, -h, h, 0.1 * dist, 10 * dist)
    return V, P


def cores_por_segmento(malha, nome_raio, onde, segs, cmap="viridis"):
    """Cor RGB (0-255) de cada segmento a partir do raio."""
    import matplotlib
    dados = malha.cell_data if onde == "cell" else malha.point_data
    r = np.asarray(dados[nome_raio], dtype=float)
    if onde == "cell" and len(r) == len(segs):
        rs = r
    elif onde == "point":
        rs = (r[segs[:, 0]] + r[segs[:, 1]]) / 2
    else:
        return np.zeros((len(segs), 3), dtype=np.uint8)
    t = (rs - rs.min()) / max(rs.max() - rs.min(), 1e-12)
    rgba = matplotlib.colormaps[cmap](t)
    return (rgba[:, :3] * 255).astype(np.uint8)


def rasterizar_modelo(malha, nome_raio, onde, M, V, P, largura, altura,
                      algoritmo=bresenham, cmap="viridis"):
    """Projeta os segmentos com M, V, P, rasteriza cada um com 'algoritmo'
    e devolve (framebuffer, segmentos_em_pixels, pixels_por_segmento)."""
    segs = md.extrair_segmentos(malha)
    pts = T.aplicar(M, np.asarray(malha.points))
    px = para_pixels(pts, V, P, largura, altura)
    cores = cores_por_segmento(malha, nome_raio, onde, segs, cmap)
    fb = novo_framebuffer(largura, altura)
    seg_px, todos = [], []
    for (i, j), cor in zip(segs, cores):
        (x0, y0), (x1, y1) = px[i], px[j]
        pix = algoritmo(int(x0), int(y0), int(x1), int(y1))
        desenhar_pixels(fb, pix, cor)
        seg_px.append(((int(x0), int(y0)), (int(x1), int(y1))))
        todos.append(pix)
    return fb, seg_px, todos


# ------------------------------------------------- Antialiasing (supersampling)
# Supersampling (SSAA) feito por nós: desenha na imagem k vezes maior, com
# Bresenham e linhas de espessura k (= 1 pixel final), e depois reduz cada
# bloco k x k para um pixel pela média (filtro de caixa). A cor do pixel final
# vira a fração da área coberta pela linha, e é isso que suaviza a escada.
def segmentos_da_arvore(malha, nome_raio, onde, M, V, P, largura, altura,
                        cmap="viridis"):
    """Segmentos em coordenadas de pixel FLUTUANTES da imagem final
    (n,4) = x0,y0,x1,y1, mais a cor RGB de cada um. Sem arredondar: quem
    decide a grade é quem rasteriza (1x para o caso sem AA, kx para SSAA)."""
    segs = md.extrair_segmentos(malha)
    pts = T.aplicar(M, np.asarray(malha.points))
    ndc = T.projetar(pts, V, P)
    x = (ndc[:, 0] + 1) / 2 * (largura - 1)
    y = (1 - ndc[:, 1]) / 2 * (altura - 1)
    xy = np.c_[x, y]
    seg_f = np.c_[xy[segs[:, 0]], xy[segs[:, 1]]]
    return seg_f, cores_por_segmento(malha, nome_raio, onde, segs, cmap)


def _pincel(k):
    """Deslocamentos (dx, dy) de um disco de diâmetro k (espessura da linha
    em pixels da imagem grande). Para k = 1 é um pixel só."""
    ini = -(k // 2)
    c = ini + (k - 1) / 2
    r2 = (k / 2) ** 2
    return [(dx, dy) for dx in range(ini, ini + k) for dy in range(ini, ini + k)
            if (dx - c) ** 2 + (dy - c) ** 2 <= r2]


def rasterizar_segmentos(seg_f, cores, largura, altura, k=1, algoritmo=bresenham):
    """Rasteriza segmentos (coordenadas do pixel final, flutuantes) numa
    imagem (altura*k, largura*k), com linhas de espessura k, e reduz por k.
    k = 1 é a rasterização normal, sem antialiasing."""
    fb = novo_framebuffer(largura * k, altura * k)
    pincel = _pincel(k)
    for (x0, y0, x1, y1), cor in zip(seg_f, cores):
        # o centro do pixel final i vira o centro do bloco k x k correspondente
        a = [int(np.rint((v + 0.5) * k - 0.5)) for v in (x0, y0, x1, y1)]
        pix = np.array(algoritmo(*a))
        for dx, dy in pincel:
            xs, ys = pix[:, 0] + dx, pix[:, 1] + dy
            ok = (xs >= 0) & (xs < largura * k) & (ys >= 0) & (ys < altura * k)
            fb[ys[ok], xs[ok]] = cor
    return reduzir(fb, k)


def reduzir(fb, k):
    """Média de cada bloco k x k (filtro de caixa)."""
    if k == 1:
        return fb
    h, w = fb.shape[0] // k, fb.shape[1] // k
    media = fb.reshape(h, k, w, k, 3).astype(float).mean(axis=(1, 3))
    return np.rint(media).astype(np.uint8)


def erro_medio_quadratico(a, b):
    """EQM entre duas imagens RGB (escala 0-255)."""
    return float(np.mean((a.astype(float) - b.astype(float)) ** 2))


# ------------------------------------------------------- Scanline Fill
# Preenchimento de polígonos (inclusive côncavos) por varredura, com tabela de
# arestas (ET) e lista de arestas ativas (AET). Vértices são pares inteiros.
# Convenções: pixel (x, y) tem o centro em (x, y); a varredura passa pelo
# centro dos pixels (y inteiro); regra par-ímpar; cada aresta cobre as
# varreduras y_min <= y < y_max (topo exclusivo, para vértices não contarem
# duas vezes) e cada trecho preenche x_a <= x < x_b (esquerda inclusiva), de
# modo que polígonos vizinhos não se sobrepõem. A conta é exata (Fraction).
from fractions import Fraction
import math


def tabela_arestas(vertices):
    """ET: uma entrada (y_min, y_max, x_em_y_min, dx, dy) por aresta não
    horizontal (arestas horizontais não cruzam nenhum centro de linha)."""
    n = len(vertices)
    arestas = []
    for i in range(n):
        (xa, ya), (xb, yb) = vertices[i], vertices[(i + 1) % n]
        if ya == yb:
            continue
        if ya > yb:
            xa, ya, xb, yb = xb, yb, xa, ya
        arestas.append((ya, yb, xa, xb - xa, yb - ya))
    return sorted(arestas)


def _x_em(aresta, y):
    """x em que a aresta cruza a varredura y, como fração exata."""
    ymin, _, x0, dx, dy = aresta
    return Fraction(x0 * dy + (y - ymin) * dx, dy)


def scanline_fill(vertices, passos=None):
    """Retorna a lista de pixels (x, y) do interior do polígono.
    Se 'passos' for uma lista, registra por varredura:
    (y, [x de cada aresta ativa, ordenados], [(x_ini, x_fim) preenchidos])."""
    et = tabela_arestas(vertices)
    if not et:
        return []
    y_ini, y_fim = et[0][0], max(a[1] for a in et)
    pixels, ativas, prox = [], [], 0
    for y in range(y_ini, y_fim):
        while prox < len(et) and et[prox][0] <= y:      # entram na AET
            ativas.append(et[prox])
            prox += 1
        ativas = [a for a in ativas if a[1] > y]       # saem da AET (y_max)
        xs = sorted(_x_em(a, y) for a in ativas)
        trechos = []
        for j in range(0, len(xs) - 1, 2):             # par-ímpar
            x_ini, x_fim = math.ceil(xs[j]), math.ceil(xs[j + 1]) - 1
            if x_ini <= x_fim:
                trechos.append((x_ini, x_fim))
                pixels.extend((x, y) for x in range(x_ini, x_fim + 1))
        if passos is not None:
            passos.append((y, [float(x) for x in xs], trechos))
    return pixels


def ponto_dentro(vertices, px, py):
    """Teste independente do scanline (não usa ET nem AET): conta os
    cruzamentos de um raio horizontal para a direita, olhando aresta por
    aresta, com a mesma regra de topo exclusivo. Serve para validar."""
    dentro = False
    n = len(vertices)
    for i in range(n):
        (xa, ya), (xb, yb) = vertices[i], vertices[(i + 1) % n]
        if (ya <= py < yb) or (yb <= py < ya):
            x_int = xa + Fraction((py - ya) * (xb - xa), yb - ya)
            if x_int > px:
                dentro = not dentro
    return dentro


def area_poligono(vertices):
    """Fórmula do cadarço (valor absoluto)."""
    s = 0
    for i in range(len(vertices)):
        (xa, ya), (xb, yb) = vertices[i], vertices[(i + 1) % len(vertices)]
        s += xa * yb - xb * ya
    return abs(s) / 2


def _testes(n=1500, seed=1):
    import random
    rng = random.Random(seed)

    # --- Bresenham
    dif = 0
    for _ in range(n):
        x0, y0, x1, y1 = (rng.randint(-30, 30) for _ in range(4))
        p = bresenham(x0, y0, x1, y1)
        assert p[0] == (x0, y0) and p[-1] == (x1, y1), "extremos"
        assert len(p) == max(abs(x1 - x0), abs(y1 - y0)) + 1, "nº de pixels"
        for a, b in zip(p, p[1:]):
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1, "conectividade"
        dx, dy = x1 - x0, y1 - y0
        for x, y in p:
            if abs(dx) >= abs(dy):
                ideal = y0 + (dy * (x - x0) / dx if dx else 0)
                assert abs(y - ideal) <= 0.5 + 1e-9, "desvio"
            else:
                ideal = x0 + dx * (y - y0) / dy
                assert abs(x - ideal) <= 0.5 + 1e-9, "desvio"
        dif += set(p) != set(dda(x0, y0, x1, y1))
    print(f"Bresenham: {n} segmentos aleatórios OK "
          f"(DDA difere em {dif} deles).")

    # --- Scanline: polígonos estrelados (simples, em geral côncavos)
    for _ in range(n // 5):
        k = rng.randint(3, 9)
        ang = sorted(rng.uniform(0, 2 * math.pi) for _ in range(k))
        v = [(round(20 + rng.uniform(4, 18) * math.cos(a)),
              round(20 + rng.uniform(4, 18) * math.sin(a))) for a in ang]
        pix = set(scanline_fill(v))
        esperado = {(x, y) for x in range(0, 41) for y in range(0, 41)
                    if ponto_dentro(v, x, y)}
        assert pix == esperado, f"scanline difere do teste de cruzamentos: {v}"
    print(f"Scanline: {n // 5} polígonos aleatórios iguais ao teste de "
          f"cruzamentos (par-ímpar exato).")
    q = [(2, 2), (12, 2), (12, 12), (2, 12)]
    assert len(scanline_fill(q)) == 100 and area_poligono(q) == 100
    q2 = [(12, 2), (22, 2), (22, 12), (12, 12)]
    assert not set(scanline_fill(q)) & set(scanline_fill(q2)), "vizinhos sobrepõem"
    print("Quadrados: 10x10 = 100 pixels; polígonos vizinhos não se sobrepõem.")


if __name__ == "__main__":
    _testes()