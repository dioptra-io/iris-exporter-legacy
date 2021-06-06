# Iris data dumps

File                              | Description
----------------------------------|------------
`uuid.json`                       | Measurement information (`GET /measurements/{uuid}`)
`uuid.nodes`                      | Nodes (one per line)
`uuid.links`                      | Links (one per line)
`results__uuid__agent.clickhouse` | Raw ClickHouse dump (`SELECT * FROM ... INTO OUTFILE ... FORMAT Native`)

The ClickHouse dumps are compressed with Zstandard (https://facebook.github.io/zstd/) which is
much faster than bzip2 and gzip while achieving similar compression ratios.
To decompress the dumps, simply run `zstd -d results__...clickhouse.zst`.

## Schema

Column              | Type          | Comments
--------------------|---------------|---------
`probe_src_addr`    | IPv6          |
`probe_dst_addr`    | IPv6          |
`probe_src_port`    | UInt16        | For ICMP the "source port" is encoded in the checksum field
`probe_dst_port`    | UInt16        |
`probe_ttl_l3`      | UInt8         | Always 0 since 08/05/2021. Removed since 04/06/2021.
`probe_ttl_l4`      | UInt8         | Renamed to `probe_ttl` since 04/06/2021.
`quoted_ttl`        | UInt8         | New since 04/06/2021.
`probe_protocol`    | UInt8         | 1 for ICMP, 58 for ICMPv6, 17 for UDP (since 30/04/2021).
`reply_src_addr`    | IPv6          |
`reply_protocol`    | UInt8         | 1 for ICMP, 58 for ICMPv6
`reply_icmp_type`   | UInt8         | 11 for ICMP Time Exceed, 3 for ICMPv6 Time Exceeded
`reply_icmp_code`   | UInt8         |
`reply_ttl`         | UInt8         |
`reply_size`        | UInt16        |
`reply_mpls_labels` | Array(UInt32) |
`rtt`               | Float64       | Float32 since 16/05/2021
`round`             | UInt8         |

## Changelog

### 30/04/2021

The `probe_protocol` column is added, to allow for multi-protocol measurements.

### 08/05/2021

We now encode `checkum(caracal_id, probe_dst_addr, probe_src_port, probe_ttl_l4)` in the IP header ID field, instead of the probe TTL (previously, `probe_ttl_l3`).
This allows us to drop invalid replies. As such the number of anomalous values in the database should be greatly reduced (TTLs > 32, probe_src_port < 24000, private probe_dst_addr, etc.).

### 16/05/2021

The RTT column precision is reduced to 32 bits as its maximum value is 6553.5 ms.

### 04/06/2021

The `probe_ttl_l4` column has been renamed to `probe_ttl` and the `probe_ttl_l3` column has been removed.
We now store `quoted_ttl`, the TTL of the probe packet as seen by the host who generated the ICMP reply.
