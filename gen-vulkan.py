import sys
import re

def writeout( out, str ):
  print( str )
  if( out ):
    out.write( '%s\n' % str )
  
  return

def buildenums( vkpath ):
  f = open( vkpath, "r" )
  strLine = '\n'
  result = ''
  enumlist = {}
  while ( len( strLine ) ):
    strLine = f.readline()

    #strLine = f.readline().replace('NV', 'Nv').replace('EXT', 'Ext').replace('AMD', 'Amd').replace('KHR', 'Khr')

    # look for enum
    m = re.search( 'typedef enum Vk.* {', strLine )
    
    if( m ):
      decl = m.group(0)
      decl = decl.replace('{', '').strip()
      enumlist[( (decl.split(' ')[2].strip() ) )] = 1

      enumChunks = re.findall('[A-Z][^A-Z]*', decl)
      enumChunks.extend( '3'*10 )
      enumOut = '/* Enum: %s */\n'  % (decl.split(' ')[2])  
      enumOut += 'enum class %s {\n' % ((decl.split(' ')[2])[2:])      
      while True:
        enumLine = f.readline()
        #print('   %s' % enumLine)
        if( enumLine.startswith('}') ):
          break
        valName = enumLine.split('=')[0]
        valChunks = valName.split('_')
        newValName = ''
        for i in range( 0, len(valChunks ) ):
          ec = enumChunks[i].upper().strip()
          vc = valChunks[i].upper().strip();
          #print(' > %s -> %s' % ( ec, vc ) )
          if( ec != vc ):
            if( (newValName == '') and (vc[0].isdigit()) ):
              newValName = '_%s' % valChunks[i-1].upper().strip()
            newValName += '_%s' % vc
                        
        enumOut += '  %s = ::%s,\n' % ( newValName[1:], valName.strip() )  
  
      enumOut += '};\n\n'
      result += enumOut
  f.close();
  print(enumlist)
  return result, enumlist

def write_comment( out ):
  s ="""/****************************************************************************
 * This file is AUTO-GENERATED and must not be modified manually.
 * Use gen-vulkan.py script to regenerate it.
 *
 * Limitations:
 * - Arrays are not supported ( like pipeline blendConstants[4] ), use 'info'
 *   instead.
 * - No platform specific structures ( Xcb, Xlib etc. )
 *
 */
"""
  writeout( out, s )
  return

def write_headers( out ):
  writeout( out, '#include <vulkan/vulkan.h>');
  writeout( out, '#include <inttypes.h>');
  writeout( out, '#include <stdint.h>');
  writeout( out, '#include <string.h>');
  return

def write_macro( out, vktype ):
  writeout( out, '\n/* Macro for Vk%s */\n' % vktype )  
  writeout( out, '#undef make_field')
  writeout( out, '#define make_field( TYPE, NAME ) \\')
  writeout( out, 'inline %s& NAME( TYPE value ) { info.NAME = value; return *this; } \\' % vktype )  
  writeout( out, 'template <typename T> \\')    
  writeout( out, 'inline %s& NAME( T value ) { info.NAME = (TYPE)value; return *this; } \\' % vktype )   
  writeout( out, 'template <typename T> \\')      
  writeout( out, 'inline %s& NAME( T* value ) { info.NAME = (TYPE)value; return *this; } \\' % vktype )  
  writeout( out, 'inline TYPE NAME() { return info.NAME; }\n')
  writeout( out, '#undef make_field_enum')
  writeout( out, '#define make_field_enum( TYPE, TYPE_VK, NAME ) \\')
  writeout( out, 'inline %s& NAME( TYPE value ) { info.NAME = (TYPE_VK)value; return *this; } \\' % vktype )
  writeout( out, '\n')
  #writeout( out, 'const TYPE&  _ ## NAME{ info.NAME } \\\n')
  return

def get_stype( vktype ):
  vk_newtype = vktype.replace("EXT", "Ext").replace("KHR", "Khr").replace("NV", "Nv").replace("AMD", "Amd")
  result = re.findall('[A-Z][^A-Z]*', vk_newtype)
  stype = 'VK_STRUCTURE_TYPE'
  for s in result:
    stype += '_%s' % s.upper()
  return stype

def write_constructor( out, vktype, found_sType ):
  writeout( out, '  %s() {' % vktype )
  writeout( out, '    memset( &info, 0, sizeof(info));' )
  if( found_sType ):
    writeout( out, '    info.sType = %s;' % get_stype(vktype) )
  writeout( out, '  }\n' )
  return

def write_operators( out, vktype ):
  writeout( out, '  inline operator %s*() { return &info; }' % vktype )
  writeout( out, '  inline operator %s&() { return info; }' % vktype )
  return

def write_field( out, strField, enumdict ):  
  fields = strField.split()  
  f = fields[ len(fields)-1 ]
  if( (f == 'sType') or ( f == 'pNext' ) ):
    return f, True

  fieldType = '%s' % fields[0]
  for i in range( 1, len(fields)-1 ):
    fieldType += ' %s' % fields[i]

  fieldType1 = fieldType;
  bodyEnum = None
  if 'Vk' in fieldType:
    m = re.search( 'Vk[a-zA-Z0-9]*', fieldType )
    if(m and enumdict.has_key( m.group(0))):
      fieldType1 = fieldType.replace('Vk', 'Vk::')
      bodyEnum = '{0:32},{1:32}, {2}'.format( fieldType1, fieldType, f );      
  body = '{0:32}, {1}'.format( fieldType, f );
  disabled = ''
  if '[' in f:
    disabled = '////'
  writeout( out, '  %smake_field( %s )' % ( disabled, body ) )
  if( bodyEnum ):
    writeout( out, '  %smake_field_enum( %s )' % ( disabled, bodyEnum ) )
  return f, False


def parse_header( headerPath, outPath ):
  
  enums, enumdict = buildenums( headerPath )
  f = open( headerPath, "r" )
  qt_snippets = open( '/tmp/snippets.xml', "w" )
  qt_snippets.write('<?xml version="1.0" encoding="UTF-8"?>\n<snippets>\n')
  out = None
  if( outPath ):
    out = open( outPath, "w" )

  strLine = '\n'
  write_comment( out )
  write_headers( out )
  writeout( out, '\nnamespace Vk {')
  writeout( out, enums )
  while ( len( strLine ) ):
    strLine = f.readline();    
    if ( not len(strLine) ):
      break

    m = re.search( 'typedef struct Vk.* {', strLine )
    if( m ):
      decl = m.group(0)
      strStructName = re.search( 'Vk.* ', decl ).group(0)

      # skip platform dependent structures
      if( re.search( ".*Xcb.*|.*Win32.*|.*Xlib.*|.*Android.*|.*Mir.*|.*Wayland.*", strStructName ) ):
        continue
 
      write_macro( out, strStructName[2:] )
      
      writeout( out, 'struct %s {' % strStructName[2:] )
      writeout( out, '  %s info;' % strStructName );
      
      snippet_xml = '<snippet group="C++" trigger="%s" id="" complement="Create Info Structure" removed="false" modified="false">' % strStructName[0:]
      snippet_inl_xml = '<snippet group="C++" trigger="%s" id="" complement="Inline Info Structure" removed="false" modified="false">' % strStructName[0:]

      snippet = 'Vk::%s$name$;\n' % strStructName[2:]
      snippet += '$name$\n';
      snippet_inl = 'Vk::%s()\n' % strStructName[2:]

      # write fields
      found_sType = False      
      while( True ):
        strField = f.readline()
        if ( strField[0] ==  "}" ):
          break
        
        strField = strField.replace(';', '')
        res, ignored = write_field( out, strField, enumdict )
        if ( res == 'sType' ):
          found_sType = True
        if( not ignored ):               
          snippet += '  .%s( 0 )\n' % res
          snippet_inl += '  .%s( 0 )\n' % res

      writeout( out, '\n  // Constructor' )
      write_constructor( out, strStructName[2:], found_sType );
      write_operators( out, strStructName )
      writeout( out, '};' )
      qt_snippets.write( '%s%s;\n</snippet>\n' % ( snippet_xml, snippet ))
      qt_snippets.write( '%s%s</snippet>\n' % ( snippet_inl_xml, snippet_inl ))
      
  f.close();
  qt_snippets.write("</snippets>\n")
  qt_snippets.close()
  writeout( out, '}')
  return

outfile = None
if( len(sys.argv) == 3 ):
  outfile = sys.argv[2]

parse_header( sys.argv[1], outfile )
#buildenums( sys.argv[1] )
#print( sys.argv ) 