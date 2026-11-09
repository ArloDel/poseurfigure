<?php

namespace App\Enums;

enum GenerationStatus: string
{
    case Pending = 'pending';
    case Generated = 'generated';
    case Failed = 'failed';
}
