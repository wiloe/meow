# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file LICENSE.rst or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION ${CMAKE_VERSION}) # this file comes with cmake

# If CMAKE_DISABLE_SOURCE_CHANGES is set to true and the source directory is an
# existing directory in our source tree, calling file(MAKE_DIRECTORY) on it
# would cause a fatal error, even though it would be a no-op.
if(NOT EXISTS "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-src")
  file(MAKE_DIRECTORY "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-src")
endif()
file(MAKE_DIRECTORY
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-build"
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix"
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/tmp"
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/src/sdl2_ttf-populate-stamp"
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/src"
  "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/src/sdl2_ttf-populate-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/src/sdl2_ttf-populate-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "C:/Users/golde/source/repos/meow/build/_deps/sdl2_ttf-subbuild/sdl2_ttf-populate-prefix/src/sdl2_ttf-populate-stamp${cfgdir}") # cfgdir has leading slash
endif()
