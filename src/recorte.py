"""
TP1 - BCC327 - Recorte de segmentos de reta (implementação própria).

  - cohen_sutherland: obrigatório. Códigos de região (outcodes) de 4 bits.
  - liang_barsky:     o segundo algoritmo implementado. Forma paramétrica.
  - cyrus_beck:       implementado só como terceiro termo de comparação e
                      validação; funciona para qualquer janela convexa.
  - sutherland_hodgman: recorte de POLÍGONOS contra janela convexa (Módulo 7).

Convenção: janela retangular (xmin, ymin, xmax, ymax), bordas incluídas.
Cada função devolve (x0, y0, x1, y1) do trecho visível ou None.
Auto-teste:  python src/recorte.py
"""
import random

# bits dos códigos de região
DENTRO, ESQ, DIR, BAIXO, CIMA = 0, 1, 2, 4, 8


# ------------------------------------------------------- Cohen–Sutherland
def codigo_regiao(x, y, janela):
    xmin, ymin, xmax, ymax = janela
    c = DENTRO
    if x < xmin:
        c |= ESQ
    elif x > xmax:
        c |= DIR
    if y < ymin:
        c |= BAIXO
    elif y > ymax:
        c |= CIMA
    return c


def cohen_sutherland(x0, y0, x1, y1, janela, passos=None, cont=None, info=None):
    """Recorte de Cohen–Sutherland.

    A cada iteração:
      1. c0 | c1 == 0  -> os dois extremos dentro: aceita (trivial)
      2. c0 & c1 != 0  -> os dois do mesmo lado de fora: rejeita (trivial)
      3. senão, escolhe um extremo fora, leva-o até uma borda violada
         (interseção) e recalcula o código dele.

    'passos' (lista), 'cont' (dict) e 'info' (dict) são opcionais e servem
    para a tabela do relatório, contagem de operações e classificação:
    info["caso"] = aceito | rejeitado | recortado | rejeitado_apos_recorte.
    """
    xmin, ymin, xmax, ymax = janela
    c0 = codigo_regiao(x0, y0, janela)
    c1 = codigo_regiao(x1, y1, janela)
    recortou = False
    it = 0
    while True:
        if not (c0 | c1):
            caso = "recortado" if recortou else "aceito"
            res = (x0, y0, x1, y1)
            break
        if c0 & c1:
            caso = "rejeitado_apos_recorte" if recortou else "rejeitado"
            res = None
            break
        fora = c0 if c0 else c1
        # as bordas são testadas na ordem CIMA, BAIXO, DIR, ESQ
        if fora & CIMA:
            x, y, borda = x0 + (x1 - x0) * (ymax - y0) / (y1 - y0), ymax, "topo"
        elif fora & BAIXO:
            x, y, borda = x0 + (x1 - x0) * (ymin - y0) / (y1 - y0), ymin, "base"
        elif fora & DIR:
            x, y, borda = xmax, y0 + (y1 - y0) * (xmax - x0) / (x1 - x0), "direita"
        else:
            x, y, borda = xmin, y0 + (y1 - y0) * (xmin - x0) / (x1 - x0), "esquerda"
        if passos is not None:
            passos.append((it, (x0, y0), c0, (x1, y1), c1,
                           f"{'P0' if fora == c0 else 'P1'} vai para a borda {borda}",
                           (x, y)))
        if cont is not None:
            cont["intersecoes"] = cont.get("intersecoes", 0) + 1
        if fora == c0:
            x0, y0 = x, y
            c0 = codigo_regiao(x0, y0, janela)
        else:
            x1, y1 = x, y
            c1 = codigo_regiao(x1, y1, janela)
        recortou = True
        it += 1
    if passos is not None:
        passos.append((it, (x0, y0), c0, (x1, y1), c1,
                       "aceita" if res else "rejeita", None))
    if info is not None:
        info["caso"] = caso
    return res


# ----------------------------------------------------------- Liang–Barsky
def liang_barsky(x0, y0, x1, y1, janela, passos=None, cont=None):
    """Recorte de Liang–Barsky: P(u) = P0 + u (P1 - P0), 0 <= u <= 1.
    Para cada borda k vale p_k * u <= q_k:
        esquerda: p = -dx, q = x0 - xmin     direita: p = dx,  q = xmax - x0
        base:     p = -dy, q = y0 - ymin     topo:    p = dy,  q = ymax - y0
    p < 0: o segmento entra pela borda (u1 = max(u1, q/p));
    p > 0: o segmento sai pela borda   (u2 = min(u2, q/p));
    p = 0: paralelo à borda; se q < 0 está fora e é rejeitado."""
    xmin, ymin, xmax, ymax = janela
    dx, dy = x1 - x0, y1 - y0
    u1, u2 = 0.0, 1.0
    bordas = (("esquerda", -dx, x0 - xmin), ("direita", dx, xmax - x0),
              ("base", -dy, y0 - ymin), ("topo", dy, ymax - y0))
    for nome, p, q in bordas:
        if p == 0:
            if q < 0:
                if passos is not None:
                    passos.append((nome, p, q, None, u1, u2, "paralelo e fora: rejeita"))
                return None
            if passos is not None:
                passos.append((nome, p, q, None, u1, u2, "paralelo e dentro: ignora"))
            continue
        r = q / p
        if cont is not None:
            cont["divisoes"] = cont.get("divisoes", 0) + 1
        if p < 0:
            u1 = max(u1, r)
            acao = "entrada: u1 = max(u1, r)"
        else:
            u2 = min(u2, r)
            acao = "saída: u2 = min(u2, r)"
        if passos is not None:
            passos.append((nome, p, q, r, u1, u2, acao))
        if u1 > u2:
            if passos is not None:
                passos.append((nome, p, q, r, u1, u2, "u1 > u2: rejeita"))
            return None
    return (x0 + u1 * dx, y0 + u1 * dy, x0 + u2 * dx, y0 + u2 * dy)


# -------------------------------------------------------------- Cyrus–Beck
def cyrus_beck(x0, y0, x1, y1, poligono):
    """Recorte contra uma janela CONVEXA qualquer (lista de vértices).
    Para cada aresta, com normal N apontando para dentro:
        N . (P(t) - A) >= 0   ->  t >= tE se N.D > 0 (entrada), t <= tL se N.D < 0.
    Vale para polígonos convexos; Liang–Barsky é o caso particular em que as
    normais são os eixos (por isso não precisa de produto escalar)."""
    n = len(poligono)
    area2 = sum(poligono[i][0] * poligono[(i + 1) % n][1]
                - poligono[(i + 1) % n][0] * poligono[i][1] for i in range(n))
    sinal = 1 if area2 > 0 else -1          # anti-horário (y para cima) = +1
    dx, dy = x1 - x0, y1 - y0
    tE, tL = 0.0, 1.0
    for i in range(n):
        ax, ay = poligono[i]
        bx, by = poligono[(i + 1) % n]
        nx, ny = -(by - ay) * sinal, (bx - ax) * sinal   # normal para dentro
        num = nx * (x0 - ax) + ny * (y0 - ay)
        den = nx * dx + ny * dy
        if den == 0:
            if num < 0:
                return None
            continue
        t = -num / den
        if den > 0:
            tE = max(tE, t)
        else:
            tL = min(tL, t)
        if tE > tL:
            return None
    return (x0 + tE * dx, y0 + tE * dy, x0 + tL * dx, y0 + tL * dy)


def janela_como_poligono(janela):
    xmin, ymin, xmax, ymax = janela
    return [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]


# ------------------------------------------------------ Sutherland–Hodgman
# Recorte de polígonos: o polígono é recortado contra UMA aresta da janela por
# vez (a saída de uma etapa é a entrada da seguinte). Para cada aresta do
# sujeito (s -> e), há 4 casos:
#     s dentro, e dentro  -> emite e
#     s dentro, e fora    -> emite a interseção
#     s fora,   e dentro  -> emite a interseção e depois e
#     s fora,   e fora    -> não emite nada
# Vale para janela CONVEXA e polígono sujeito qualquer. Se o sujeito é côncavo
# e o resultado deveria ter várias partes separadas, o algoritmo as liga por
# arestas degeneradas (sobre a borda da janela). O Weiler–Atherton evita isso.
def _orientacao(poligono):
    n = len(poligono)
    a2 = sum(poligono[i][0] * poligono[(i + 1) % n][1]
             - poligono[(i + 1) % n][0] * poligono[i][1] for i in range(n))
    return 1 if a2 > 0 else -1


def _lado(p, a, b):
    """> 0 se p está à esquerda da aresta a->b."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def _intersecao_retas(p, q, a, b):
    """Ponto onde a reta p-q cruza a reta a-b (supõe que não são paralelas)."""
    x1, y1, x2, y2 = p[0], p[1], q[0], q[1]
    x3, y3, x4, y4 = a[0], a[1], b[0], b[1]
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def sutherland_hodgman(sujeito, janela, etapas=None):
    """Recorta o polígono 'sujeito' (lista de vértices) contra a janela
    convexa 'janela' (lista de vértices, qualquer orientação).
    'etapas' (lista) recebe, após cada aresta da janela, ((a, b), vértices)."""
    sinal = _orientacao(janela)
    saida = [tuple(p) for p in sujeito]
    n = len(janela)
    for i in range(n):
        a, b = janela[i], janela[(i + 1) % n]
        entrada, saida = saida, []
        if not entrada:
            if etapas is not None:
                etapas.append(((a, b), []))
            continue

        def dentro(p):
            return _lado(p, a, b) * sinal >= 0

        s = entrada[-1]
        for e in entrada:
            if dentro(e):
                if not dentro(s):
                    saida.append(_intersecao_retas(s, e, a, b))
                saida.append(e)
            elif dentro(s):
                saida.append(_intersecao_retas(s, e, a, b))
            s = e
        saida = _sem_repetidos(saida)
        if etapas is not None:
            etapas.append(((a, b), list(saida)))
    return saida


def _sem_repetidos(lista, tol=1e-12):
    """Tira vértices consecutivos iguais (surgem quando a interseção cai
    exatamente num vértice ou num canto da janela)."""
    if not lista:
        return lista
    out = [lista[0]]
    for p in lista[1:]:
        if abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) <= tol \
            and abs(out[0][1] - out[-1][1]) <= tol:
        out.pop()
    return out


def trechos_degenerados(poligono, tol=1e-9):
    """Trechos em que duas arestas do polígono se sobrepõem em sentidos
    opostos (as 'pontes' de largura zero do Sutherland–Hodgman)."""
    n = len(poligono)
    arestas = [(poligono[i], poligono[(i + 1) % n]) for i in range(n)]
    achados = []
    for i in range(n):
        p1, p2 = arestas[i]
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        d2 = dx * dx + dy * dy
        if d2 == 0:
            continue
        for j in range(n):
            if j == i:
                continue
            q1, q2 = arestas[j]
            ex, ey = q2[0] - q1[0], q2[1] - q1[1]
            if dx * ex + dy * ey >= 0:
                continue                      # mesmo sentido
            c1 = dx * (q1[1] - p1[1]) - dy * (q1[0] - p1[0])
            c2 = dx * (q2[1] - p1[1]) - dy * (q2[0] - p1[0])
            if abs(c1) > tol * (1 + d2) or abs(c2) > tol * (1 + d2):
                continue                      # não colineares
            t1 = ((q1[0] - p1[0]) * dx + (q1[1] - p1[1]) * dy) / d2
            t2 = ((q2[0] - p1[0]) * dx + (q2[1] - p1[1]) * dy) / d2
            lo, hi = max(0.0, min(t1, t2)), min(1.0, max(t1, t2))
            if hi - lo > 1e-9:
                achados.append(((p1[0] + lo * dx, p1[1] + lo * dy),
                                (p1[0] + hi * dx, p1[1] + hi * dy)))
    return achados


def area_poligono_f(poligono):
    n = len(poligono)
    return abs(sum(poligono[i][0] * poligono[(i + 1) % n][1]
                   - poligono[(i + 1) % n][0] * poligono[i][1]
                   for i in range(n))) / 2


def _par_impar(poligono, x, y):
    """Teste par-ímpar em ponto flutuante (usado só para validar)."""
    dentro = False
    n = len(poligono)
    for i in range(n):
        (xa, ya), (xb, yb) = poligono[i], poligono[(i + 1) % n]
        if (ya <= y < yb) or (yb <= y < ya):
            if xa + (y - ya) * (xb - xa) / (yb - ya) > x:
                dentro = not dentro
    return dentro


# ------------------------------------------------------------- auto-teste
def _iguais(a, b, tol=1e-7):
    if a is None or b is None:
        return a is b
    return all(abs(u - v) <= tol for u, v in zip(a, b))


def _comprimento(r):
    return ((r[2] - r[0]) ** 2 + (r[3] - r[1]) ** 2) ** 0.5


def _testes(n=20000, seed=3):
    rng = random.Random(seed)
    cont = {k: 0 for k in ("aceito", "rejeitado", "recortado", "rejeitado_apos_recorte")}
    for _ in range(n):
        xa, xb = sorted(rng.uniform(-20, 20) for _ in range(2))
        ya, yb = sorted(rng.uniform(-20, 20) for _ in range(2))
        if xb - xa < 1 or yb - ya < 1:
            continue
        j = (xa, ya, xb, yb)
        s = [rng.uniform(-30, 30) for _ in range(4)]
        info = {}
        cs = cohen_sutherland(*s, j, info=info)
        lb = liang_barsky(*s, j)
        cb = cyrus_beck(*s, janela_como_poligono(j))
        cont[info["caso"]] += 1
        # casos degenerados (só encosta num canto) podem divergir: ignora
        if cs is not None and _comprimento(cs) < 1e-9:
            continue
        assert _iguais(cs, lb), f"CS x LB: {s} {j} -> {cs} {lb}"
        assert _iguais(cs, cb), f"CS x CB: {s} {j} -> {cs} {cb}"
        if cs is not None:     # trecho dentro da janela e sobre a reta original
            for x, y in ((cs[0], cs[1]), (cs[2], cs[3])):
                assert xa - 1e-9 <= x <= xb + 1e-9 and ya - 1e-9 <= y <= yb + 1e-9
                cruz = (s[2] - s[0]) * (y - s[1]) - (s[3] - s[1]) * (x - s[0])
                assert abs(cruz) < 1e-6 * (1 + _comprimento(s))
    print(f"{n} segmentos/janelas aleatórios: Cohen–Sutherland, Liang–Barsky e "
          f"Cyrus–Beck concordam; trechos ficam dentro da janela e sobre a reta.")
    print("Casos (Cohen–Sutherland):",
          ", ".join(f"{k}={v}" for k, v in cont.items()))

    # --- Sutherland–Hodgman: polígonos estrelados (em geral côncavos) contra
    # janelas retangulares. O ponto está no resultado <=> está no sujeito E na
    # janela (pontos amostrados ao acaso; o par-ímpar ignora as arestas
    # degeneradas que o SH cria quando o resultado tem partes separadas).
    import math
    npoly = 600
    for _ in range(npoly):
        k = rng.randint(3, 10)
        ang = sorted(rng.uniform(0, 2 * math.pi) for _ in range(k))
        suj = [(rng.uniform(-3, 3) + (10 + rng.uniform(4, 14)) * math.cos(a),
                (10 + rng.uniform(4, 14)) * math.sin(a)) for a in ang]
        xa, xb = sorted(rng.uniform(-18, 18) for _ in range(2))
        ya, yb = sorted(rng.uniform(-18, 18) for _ in range(2))
        if xb - xa < 2 or yb - ya < 2:
            continue
        res = sutherland_hodgman(suj, janela_como_poligono((xa, ya, xb, yb)))
        for _ in range(60):
            x, y = rng.uniform(-25, 30), rng.uniform(-25, 25)
            esperado = (xa <= x <= xb and ya <= y <= yb
                        and _par_impar(suj, x, y))
            obtido = len(res) >= 3 and _par_impar(res, x, y)
            assert esperado == obtido, f"SH errado: {suj} {(xa, ya, xb, yb)} ({x},{y})"
    print(f"Sutherland–Hodgman: {npoly} polígonos (côncavos incluídos) contra "
          f"janelas aleatórias, 60 pontos cada: região resultante correta.")
    q = [(0, 0), (4, 0), (4, 4), (0, 4)]
    assert abs(area_poligono_f(sutherland_hodgman(q, janela_como_poligono((2, 2, 6, 6)))) - 4) < 1e-9
    assert sutherland_hodgman(q, janela_como_poligono((10, 10, 12, 12))) == []
    print("Quadrado 4x4 contra janela (2,2)-(6,6): área 4; janela disjunta: vazio.")


if __name__ == "__main__":
    _testes()