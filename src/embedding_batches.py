def montar_lotes(itens, max_vagas = 20, max_tokens=20000):
    if max_vagas <= 0 or max_tokens <= 0:
        raise ValueError("Os limites precisam ser positivos.")

    lote = []
    tokens_lote = 0

    for item in itens:
        tokens  = item["tokens"]

        if tokens <= 0 or tokens > max_tokens:
            raise ValueError(
                f"Entrada com {tokens} tokens não cabe em um lote"
            )

        if lote and (
            len(lote) >= max_vagas
            or tokens_lote + tokens > max_tokens
        ):
            yield lote
            lote = []
            tokens_lote = 0


        lote.append(item)
        tokens_lote += tokens


    if lote:
        yield lote
