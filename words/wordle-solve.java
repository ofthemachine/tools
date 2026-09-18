#!/usr/bin/env -S fragletc --image=100hellos/java@sha256:2b8b7b5817381f6d9460e2b4a124ad5f0ca01d668d4db084690a45939831b909 --mode=wordalytica
#: d=Filter possible 5-letter Wordle answers given one or more guess+feedback rounds, using 100hellos/java's real wordalytica fluent WordSet API and word list (not a reimplementation). clues is "guess:result|guess:result|...", each result a 5-char G/Y/X string matching that guess letter-for-letter (G=green/correct spot, Y=yellow/wrong spot, X=gray/absent), e.g. "crane:GYXXX|mount:XXGXY". Report the raw colors you see -- this tool does the Wordle-logic-to-predicate translation, not you.
#: when=Use when the user is solving a Wordle and reports the colours from one or more guesses.
#: network=none
#: stdin=none
#: param=clues:required:d=guess:result rounds joined by |; result is 5 chars of G/Y/X, e.g. crane:GYXXX|mount:XXGXY

String clues = System.getenv("CLUES");
com.wordalytica.wordset.core.WordSet<?> words = Wordalytica.loadWords().matching("_____");
for (String round : clues.split("\\|")) {
    String[] parts = round.split(":");
    String guess = parts[0].toLowerCase();
    String result = parts[1].toUpperCase();
    for (int i = 0; i < 5; i++) {
        char g = guess.charAt(i);
        char r = result.charAt(i);
        if (r == 'G') {
            words = words.withCharAt(g, i);
        } else if (r == 'Y') {
            words = words.containing(String.valueOf(g)).withoutCharAt(g, i);
        } else {
            words = words.withoutCharAt(g, i);
            boolean elsewhere = false;
            for (int j = 0; j < 5; j++) {
                if (result.charAt(j) != 'X' && guess.charAt(j) == g) elsewhere = true;
            }
            if (!elsewhere) words = words.notContaining(String.valueOf(g));
        }
    }
}
// Exactly one terminal call: WordSetV2's count()/iterator() both reset the
// predicate builder as a side effect (WordSetV2.predicate(true)), so a
// second terminal call on the same instance runs unconstrained -- found
// live, calling count() then iterator() silently returned every word in
// the dictionary. Materialize once, derive count and sample from that.
java.util.List<String> matches = new java.util.ArrayList<>();
words.iterator().forEachRemaining(matches::add);
java.util.Collections.sort(matches);
int total = matches.size();
int shown = Math.min(20, total);
for (int i = 0; i < shown; i++) System.out.println(matches.get(i));
if (total > shown) System.out.println("... and " + (total - shown) + " more (" + total + " total)");
