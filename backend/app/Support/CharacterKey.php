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
}
