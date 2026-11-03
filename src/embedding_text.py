import html
import hashlib
import tiktoken

TOKENIZADOR = tiktoken.get_encoding("cl100k_base")
MAX_TOKENS = 8000


def normalizar_texto(texto: str | None) -> str:
    if texto is None:
        return ""

    texto = html.unescape(texto)
    return " ".join(texto.split())

def preparar_texto(vaga: dict, variacao: str) -> str:
    titulo = normalizar_texto(vaga.get("nome"))

    if not titulo:
        raise ValueError("A vaga precisa ter um título.")

    if variacao == "titulo":
        return f"Título: {titulo}"

    if variacao == "titulo_empresa_descricao":
        empresa = normalizar_texto(vaga.get("empresa"))
        descricao = normalizar_texto(vaga.get("descricao"))

        partes = [f"Título: {titulo}"]

        if empresa:
            partes.append(f'Empresa: {empresa}')

        if descricao:
            partes.append(f'Descrição: {descricao}')

        return "\n".join(partes)

    raise ValueError(f"Variação desconhecida: {variacao}")

def calcular_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def validar_texto(texto: str) -> int:
    if not texto.strip():
        raise ValueError("O texto do embedding não pode estar vazio.")

    quantidade = len(
        TOKENIZADOR.encode(texto, disallowed_special=())
    )

    if quantidade > MAX_TOKENS:
        raise ValueError(
            f"Texto com {quantidade} tokens; "
            f"limite permitido: {MAX_TOKENS}"
        )

    return quantidade
