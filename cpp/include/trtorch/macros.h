/*
 * Copyright (c) NVIDIA Corporation.
 * All rights reserved.
 *
 * This library is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree.
 */
#pragma once

#if defined(__GNUC__)
#define TRTORCH_API __attribute__((__visibility__("default")))
#define TRTORCH_HIDDEN __attribute__((__visibility__("hidden")))
#else
#define TRTORCH_API
#define TRTORCH_HIDDEN
#endif // defined(__GNUC__)

// Does this need to be gaurded or something?
#define XSTR(x) #x
#define STR(x) XSTR(x)

#define TRTORCH_MAJOR_VERSION 0
#define TRTORCH_MINOR_VERSION 5
#define TRTORCH_PATCH_VERSION 0
#define TRTORCH_VERSION      \
  STR(TRTORCH_MAJOR_VERSION) \
  "." STR(TRTORCH_MINOR_VERSION) "." STR(TRTORCH_PATCH_VERSION)
