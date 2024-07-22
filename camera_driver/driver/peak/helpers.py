from ids_peak import ids_peak

class NodeException(Exception):
  def __init__(self, msg):
    super(NodeException, self).__init__(msg)

def find_node(nodemap:ids_peak.NodeMap, node_name:str):
  node = nodemap.FindNode(node_name)
  if node is None:
    raise NodeException(f"Node {node_name} not found")

  return node

def node_value(nodemap:ids_peak.NodeMap, node_name:str):
  node = get_readable(nodemap, node_name)

  if node.Type() == ids_peak.NodeType_Enumeration:
    return node.CurrentEntry().DisplayName()
  else:
    return node.Value()
  
def is_readable(nodemap:ids_peak.NodeMap, node_name:str):
  node = nodemap.FindNode(node_name)
  return node is not None and (node.AccessStatus() in [ids_peak.NodeAccessStatus_ReadOnly, ids_peak.NodeAccessStatus_ReadWrite])

def is_writable(nodemap:ids_peak.NodeMap, node_name:str):
  node = nodemap.FindNode(node_name)
  return node is not None and (node.AccessStatus() in [ids_peak.NodeAccessStatus_WriteOnly, ids_peak.NodeAccessStatus_ReadWrite])

def get_writable(nodemap:ids_peak.NodeMap, node_name:str):
  node = find_node(nodemap, node_name)

  if (node.AccessStatus() in [ids_peak.NodeAccessStatus_WriteOnly, ids_peak.NodeAccessStatus_ReadWrite]):
    return node
  
  raise NodeException(f"Node {node_name} is {ids_peak.NodeAccessStatusEnumEntryToString(node.AccessStatus())}")

def get_readable(nodemap:ids_peak.NodeMap, node_name:str):
  node = find_node(nodemap, node_name)

  if (node.AccessStatus() in [ids_peak.NodeAccessStatus_ReadOnly, ids_peak.NodeAccessStatus_ReadWrite]):
    return node
  
  raise NodeException(f"Node {node_name} is {ids_peak.NodeAccessStatusEnumEntryToString(node.AccessStatus())}")

def set_value(nodemap:ids_peak.NodeMap, node_name:str, value):
  node = get_writable(nodemap, node_name)

  if node.Type() == ids_peak.NodeType_Enumeration:
    try:
      entry = node.FindEntry(value)
    except ids_peak.NotFoundException as e:
      options = [e.DisplayName() for e in node.Entries()]
      raise NodeException(f"Entry {value} not found in node {node_name}: {options}")

    node.SetCurrentEntry(entry)

  else:
    node.SetValue(value)


def execute_wait(nodemap:ids_peak.NodeMap, node_name:str):
    node = find_node(nodemap, node_name)

    node.Execute()
    node.WaitUntilDone()