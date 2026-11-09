<?php

namespace App\Enums;

/** A generated image is never presented as verified unless it is `Validated` (REC-10). */
enum ValidationStatus: string
{
    case Unvalidated = 'unvalidated';
    case Validated = 'validated';
    case Rejected = 'rejected';
}
