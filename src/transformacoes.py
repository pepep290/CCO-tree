"""
TP1 - BCC327 - Módulo 2: transformações geométricas e câmera.

Tudo aqui é numpy puro (sem PyVista/VTK), para que a matemática seja do grupo
e não uma caixa-preta. Convenção: coordenadas homogêneas, vetores coluna,
matrizes 4x4, sistema de mão direita (como o OpenGL).

    p_clip = P @ V @ M @ p_mundo_original
    M = matriz de modelo   (objeto -> mundo)
    V = matriz de vista    (mundo  -> câmera)
    P = matriz de projeção (câmera -> espaço de recorte)
    NDC = p_clip[:3] / p_clip[3]   (divisão perspectiva)
"""
import numpy as np


# ---------------------------------------------------------------- modelo (M)
def translacao(tx, ty, tz):
    M = np.eye(4)
    M[:3, 3] = (tx, ty, tz)
    return M


def escala(sx, sy=None, sz=None):
    sy = sx if sy is None else sy
    sz = sx if sz is None else sz
    return np.diag([sx, sy, sz, 1.0])


def rotacao_x(graus):
    c, s = np.cos(np.radians(graus)), np.sin(np.radians(graus))
    M = np.eye(4)
    M[1, 1], M[1, 2], M[2, 1], M[2, 2] = c, -s, s, c
    return M


def rotacao_y(graus):
    c, s = np.cos(np.radians(graus)), np.sin(np.radians(graus))
    M = np.eye(4)
    M[0, 0], M[0, 2], M[2, 0], M[2, 2] = c, s, -s, c
    return M


def rotacao_z(graus):
    c, s = np.cos(np.radians(graus)), np.sin(np.radians(graus))
    M = np.eye(4)
    M[0, 0], M[0, 1], M[1, 0], M[1, 1] = c, -s, s, c
    return M


def rotacao_xyz(rx, ry, rz):
    """Aplica primeiro X, depois Y, depois Z (R = Rz @ Ry @ Rx)."""
    return rotacao_z(rz) @ rotacao_y(ry) @ rotacao_x(rx)


def matriz_modelo(trans, rot, esc, centro):
    """M = T(trans) @ T(c) @ R @ S @ T(-c).
    Rotação e escala acontecem em torno do centro do modelo (senão a árvore
    giraria em torno da origem e sairia da tela); a translação move o
    conjunto depois."""
    c = np.asarray(centro, float)
    return (translacao(*trans) @ translacao(*c) @ rotacao_xyz(*rot)
            @ escala(esc) @ translacao(*(-c)))


# ---------------------------------------------------------------- vista (V)
def olhar_para(eye, alvo, up):
    """Equivalente ao gluLookAt. Constrói a base da câmera:
        f = direção para onde olha, s = direita, u = cima verdadeiro.
    A câmera olha para -z no seu próprio sistema."""
    eye, alvo, up = (np.asarray(v, float) for v in (eye, alvo, up))
    f = alvo - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    V = np.eye(4)
    V[0, :3], V[1, :3], V[2, :3] = s, u, -f
    V[:3, 3] = -V[:3, :3] @ eye
    return V


# ------------------------------------------------------------- projeção (P)
def ortografica(l, r, b, t, n, f):
    P = np.eye(4)
    P[0, 0], P[0, 3] = 2 / (r - l), -(r + l) / (r - l)
    P[1, 1], P[1, 3] = 2 / (t - b), -(t + b) / (t - b)
    P[2, 2], P[2, 3] = -2 / (f - n), -(f + n) / (f - n)
    return P


def perspectiva(fovy_graus, aspecto, n, f):
    k = 1.0 / np.tan(np.radians(fovy_graus) / 2)
    P = np.zeros((4, 4))
    P[0, 0] = k / aspecto
    P[1, 1] = k
    P[2, 2] = (f + n) / (n - f)
    P[2, 3] = 2 * f * n / (n - f)
    P[3, 2] = -1.0
    return P


# --------------------------------------------------------------- utilidades
def aplicar(M, pontos):
    """Aplica uma matriz afim 4x4 a pontos (N,3) -> (N,3)."""
    h = np.c_[pontos, np.ones(len(pontos))]
    return (h @ M.T)[:, :3]


def projetar(pontos, V, P):
    """Pontos do mundo (N,3) -> coordenadas NDC (N,3), com divisão por w."""
    h = np.c_[pontos, np.ones(len(pontos))]
    clip = h @ (P @ V).T
    return clip[:, :3] / clip[:, 3:4]


# Vistas predefinidas: (direção do olho a partir do alvo, vetor "cima")
VISTAS = {
    "frontal":    ((0, 0, 1), (0, 1, 0)),
    "lateral":    ((1, 0, 0), (0, 1, 0)),
    "topo":       ((0, 1, 0), (0, 0, -1)),
    "isometrica": ((1, 1, 1), (0, 1, 0)),
}


def camera_da_vista(nome, centro, distancia):
    direcao, up = VISTAS[nome]
    d = np.asarray(direcao, float)
    d /= np.linalg.norm(d)
    eye = np.asarray(centro, float) + distancia * d
    return eye, np.asarray(centro, float), np.asarray(up, float)