#!/usr/bin/env bash
# Roda o lote noturno do iastro em background e registra tudo num log.
# Pode ficar de madrugada; qualquer falha é anotada sem parar o restante.
#
# Uso:
#   chmod +x rodar_noite.sh
#   REPETE=12 ./rodar_noite.sh      # repete 12 rodadas, espaçadas de ESPERA min
#   nohup ./rodar_noite.sh >/dev/null 2>&1 &
#   tail -f /mnt/dados/home-italivre/iastro-ia/mapas/exemplos/rodada-noite.log
set -u

EPH=/mnt/dados/ephemeris
PY=/mnt/dados/home-italivre/iastro-ia/venv/bin/python
SAI=/mnt/dados/home-italivre/iastro-ia/mapas/exemplos
LOG="$SAI/rodada-noite.log"
REPETE="${REPETE:-1}"      # quantas rodadas (1 = só uma)
ESPERA="${ESPERA:-300}"    # segundos entre rodadas (padrão 5 min)

mkdir -p "$SAI"

for ((i=1; i<=REPETE; i++)); do
  echo "== $(date '+%F %T') início da rodada $i/$REPETE ==" >> "$LOG"

  # 1) garante banco consistente
  cd /mnt/dados/home-italivre/iastro-ia/arquetipos
  "$PY" construir_banco.py >> "$LOG" 2>&1 \
    && echo "banco reconstruído" >> "$LOG" || echo "AVISO: banco não reconstruiu" >> "$LOG"

  # 2) cultura de céu + lote
  cd "$EPH"
  "$PY" ceu.py --gerar >> "$LOG" 2>&1
  "$PY" gerar_lote.py --saida "$SAI" >> "$LOG" 2>&1

  # 3) disco no fim
  du -sh "$SAI" >> "$LOG"
  echo "== $(date '+%F %T') fim da rodada $i ==" >> "$LOG"

  if (( i < REPETE )); then
    echo "— espera $ESPERA s antes da próxima rodada —" >> "$LOG"
    sleep "$ESPERA"
  fi
done
echo "rodadas concluídas. log: $LOG"