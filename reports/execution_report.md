# Reporte de Ejecución

## Conteos de Silver (idempotencia, REQ-S4)

| métrica | corrida 1 | corrida 2 |
|---|---|---|
| filas_leidas | 1000 | 1000 |
| filas_validas | 994 | 994 |
| filas_en_cuarentena | 6 | 6 |
| filas_nuevas | 994 | 0 |
| filas_actualizadas | 0 | 0 |
| filas_totales_silver | 994 | 994 |

## Comparativa de motores vectoriales (REQ-G0)

| motor | tiempo_construccion_ms | latencia_p50_ms | latencia_p95_ms | recall_at_k | huella_disco_bytes | elegido |
|---|---|---|---|---|---|---|
| faiss.IndexFlatIP | 0.416 | 0.0691 | 0.0869 | 1.0 | 1526829 | ✓ |
| usearch.Index (HNSW) | 30.085 | 0.0794 | 0.0887 | 1.0 | 1673840 |  |

**Motor elegido:** faiss.IndexFlatIP — Empate en recall@k (1.000) entre faiss.IndexFlatIP, usearch.Index (HNSW); gana faiss.IndexFlatIP por menor huella en disco (1526829 bytes).

## Top 3 de búsqueda semántica (REQ-G3)

Query: "pirates searching for treasure"

| id | title_romaji | score | synopsis |
|---|---|---|---|
| 465 | ONE PIECE THE MOVIE: Karakuri-jou no Mecha Kyohei | 0.6065 | The crew salvages a treasure chest from a sinking wreck, but inside turns out to be an old lady hiding. To get the Straw Hat Pirates to take her home, she promi… |
| 459 | ONE PIECE (Movie) | 0.5959 | There once was a pirate known as the Great Gold Pirate Woonan, who obtained almost 1/3 of the world's gold. Over the course of a few years, the pirate's existen… |
| 21 | ONE PIECE | 0.5337 | Gold Roger was known as the Pirate King, the strongest and most infamous being to have sailed the Grand Line. The capture and death of Roger by the World Govern… |
