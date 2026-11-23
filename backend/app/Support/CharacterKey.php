<?php

namespace App\Support;

/**
 * Comparable form of a character name, the same rule as the AI service (figure_identifier.character_key):
 * "Spider-Man (Symbiote Suit)" and "spiderman" both give "spiderman". Variants in brackets are dropped.
 */
final class CharacterKey
{
    public static function from(?string $name): string
    {
        if ($name === null) {
            return '';
        }
        $base = preg_replace('/\(.*?\)/', ' ', mb_strtolower($name));

        return (string) preg_replace('/[^a-z0-9]/', '', (string) $base);
    }

    /**
     * Same character, as the AI service decides it (figure_identifier.same_character): equal keys, or one key
     * starting with the other ("spidermansymbiotesuit" and "spiderman"), if the shorter has 4+ letters.
     */
    public static function same(?string $a, ?string $b): bool
    {
        [$ka, $kb] = [self::from($a), self::from($b)];
        if ($ka === '' || $kb === '') {
            return false;
        }
        [$short, $long] = strlen($ka) <= strlen($kb) ? [$ka, $kb] : [$kb, $ka];

        return $ka === $kb || (strlen($short) >= 4 && str_starts_with($long, $short));
    }
}
