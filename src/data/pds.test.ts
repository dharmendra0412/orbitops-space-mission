import { describe, expect, it } from 'vitest'
import { extractPdsFileManifest, extractPdsMembers, extractPdsProducts, mergePdsMembers } from './pds'

describe('NASA PDS response adapters', () => {
  it('reads the documented KVP search response without inventing missing fields', () => {
    const result = extractPdsProducts({
      summary: { hits: 1 },
      data: [{ lidvid: 'urn:nasa:pds:example::1.0', title: 'Example collection' }],
    })
    expect(result).toEqual({
      hits: 1,
      products: [{ lidvid: 'urn:nasa:pds:example::1.0', title: 'Example collection' }],
    })
  })

  it('represents a genuine empty PDS search response as zero products', () => {
    expect(extractPdsProducts([])).toEqual({ hits: 0, products: [] })
  })

  it('extracts hierarchy records using the source id field', () => {
    expect(extractPdsMembers([
      { id: 'urn:nasa:pds:example:item::1.0', title: 'Source title', type: 'Product_Observational' },
    ])).toEqual([
      { id: 'urn:nasa:pds:example:item::1.0', title: 'Source title', type: 'Product_Observational', start_date_time: undefined, stop_date_time: undefined },
    ])
  })


  it('deduplicates repeated PDS member identifiers while preserving first-seen order', () => {
    const first = { id: 'urn:nasa:pds:example:item-1::1.0', title: 'First page title' }
    const second = { id: 'urn:nasa:pds:example:item-2::1.0', title: 'Second page title' }
    const repeated = { id: first.id, title: 'Repeated page title' }

    expect(mergePdsMembers([first], [repeated, second, second])).toEqual([first, second])
  })

  it('reads file references and checksums from the documented PDS registry metadata', () => {
    const result = extractPdsFileManifest({
      meta: {
        'ops:Label_File_Info': {
          'ops:file_name': 'collection.xml',
          'ops:file_ref': '/data/collection.xml',
          'ops:file_size': '8655',
          'ops:md5_checksum': 'aa584be2cd34d1899f19d39c23cccba1',
        },
        'ops:Data_Files': [{
          'ops:file_name': 'table.csv',
          'ops:file_ref': '/data/table.csv',
          'ops:file_size': '1024',
          'ops:md5_checksum': 'cd24cbc46c45ed023f039b3e2beb6606',
          'ops:mime_type': 'text/csv',
        }],
      },
    })
    expect(result).toEqual([
      { role: 'label', fileName: 'collection.xml', fileReference: '/data/collection.xml', sizeBytes: '8655', md5: 'aa584be2cd34d1899f19d39c23cccba1', mimeType: undefined },
      { role: 'data', fileName: 'table.csv', fileReference: '/data/table.csv', sizeBytes: '1024', md5: 'cd24cbc46c45ed023f039b3e2beb6606', mimeType: 'text/csv' },
    ])
  })

  it('does not fabricate file records when PDS metadata has no file inventory', () => {
    expect(extractPdsFileManifest({ id: 'urn:nasa:pds:example::1.0' })).toEqual([])
  })
})
