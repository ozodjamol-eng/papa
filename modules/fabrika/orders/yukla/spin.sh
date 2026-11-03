cd /home/claude/yukla_promo
python3 bolt_final.py -- -18 128 1400 /home/claude/yukla_promo/bolt/hero.png > /dev/null 2>&1
mkdir -p bolt/spin
for i in $(seq 0 29); do
  a=$(python3 -c "t=$i/29;e=1-(1-t)**3;print(round(200+(-18-200)*e,2))")
  python3 bolt_final.py -- $a 32 720 /home/claude/yukla_promo/bolt/spin/$(printf %02d $i).png > /dev/null 2>&1
done
echo DONE
