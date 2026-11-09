<?php

namespace App\Enums;

enum AnalysisMode: string
{
    /** The system classifies the figure profile itself. */
    case Automatic = 'automatic';

    /** The user picked the figure profile. */
    case Manual = 'manual';
}
