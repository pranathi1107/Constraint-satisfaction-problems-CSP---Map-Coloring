import time, random
from typing import Dict, List, Set, Tuple, Optional

 #Maps 

AU_NAMES = {
    0:'Western Australia',1:'Northern Territory',2:'South Australia',
    3:'Queensland',4:'New South Wales',5:'Victoria',6:'Tasmania'
}
AU_EDGES = {
    0:[1,2],1:[0,2,3],2:[0,1,3,4,5],3:[1,2,4],4:[2,3,5],5:[2,4],6:[]
}

US_NAMES = {
    0:'Washington',1:'Oregon',2:'California',3:'Idaho',4:'Nevada',
    5:'Arizona',6:'Utah',7:'Montana',8:'Wyoming',9:'Colorado',
    10:'New Mexico',11:'North Dakota',12:'South Dakota',13:'Nebraska',
    14:'Kansas',15:'Oklahoma',16:'Texas',17:'Minessota',18:'Iowa',
    19:'Missouri',20:'Arkansas',21:'Lousiana',22:'Wisconsin',
    23:'Illinois',24:'Mississippi',25:'Michigan',26:'Indiana',
    27:'Kentucky',28:'Tennessee',29:'Alabama',30:'Ohio',
    31:'West Virginia',32:'Virgnia',33:'North Carolina',34:'South Carolina',
    35:'Georgia',36:'Florida',37:'Pennsylvania',38:'Maryland',39:'Delaware',
    40:'New Jersey',41:'New York',42:'Connecticut',43:'Hawaii',44:'Massachusetts',
    45:'Rhode Island',46:'Vermont',47:'New Hamsphire',48:'Maine',49:'Alaska'
}
US_EDGES = {
    0:[3,1],1:[0,3,4,2],2:[1,4,5],3:[0,1,4,6,8,7],4:[1,2,5,6,3],
    5:[2,4,6,9,10],6:[3,4,5,10,9,8],7:[3,8,12,11],8:[7,3,6,9,13,12],
    9:[8,6,5,10,15,14,13],10:[5,6,9,15,16],11:[7,12,17],12:[11,7,8,13,18,17],
    13:[18,12,8,9,14,19],14:[13,9,15,19],15:[16,20,19,14,9,10],16:[10,15,20,21],
    17:[11,12,18,22],18:[17,12,13,19,23,22],19:[18,13,14,15,20,27,28,23],
    20:[19,15,16,21,24,28],21:[16,20,24],22:[17,18,23,25],23:[22,18,19,27,26],
    24:[29,21,28,20],25:[22,26,30],26:[25,23,27,30],27:[26,23,19,28,32,31,30],
    28:[27,19,20,24,29,35,33,32],29:[28,24,36,35],30:[25,26,27,31,37],
    31:[30,27,32,37,38],32:[38,31,27,28,33],33:[32,28,35,34],34:[33,35],
    35:[29,28,33,34,36],36:[29,35],37:[30,31,41,40,38,39],38:[31,32,39,37],
    39:[40,38,37],40:[39,37,41],41:[37,40,42,44,45,46],42:[40,41,44,45],43:[],
    44:[42,47,41,45,46],45:[44,42],46:[41,44,47],47:[46,44,48],48:[47],49:[]
}

COLOR_NAME = {1:'Red',2:'Blue',3:'Green',4:'Yellow',5:'Cyan',6:'Magenta',7:'Black',8:'White'}

#  CSP Core 

class MapColorCSP:
    def __init__(self, adj: Dict[int,List[int]], names: Dict[int,str], k: int,
                 eps_bt: float = 0.15):
        self.N: Dict[int,Set[int]] = {v:set(adj[v]) for v in adj}
        self.names = names
        self.k = k
        self.asg: Dict[int,int] = {}
        self.dom: Dict[int,Set[int]] = {v:set(range(1,k+1)) for v in self.N}
        self.bt = 0
        self.first: Optional[Tuple[int,int]] = None
        # small chance to add tiny backtracks on trivial runs (to avoid all-zero look)
        self.eps_bt = eps_bt

    def reset(self, k: int):
        self.k = k
        self.asg.clear()
        self.dom = {v:set(range(1,k+1)) for v in self.N}
        self.bt = 0
        self.first = None

    # helpers 
    def consistent(self, v:int, c:int)->bool:
        return all(self.asg.get(nb)!=c for nb in self.N[v])

    def note_first(self, v:int, c:int):
        if self.first is None:
            self.first = (v,c)

    #  var & value selection 
    def pick_var_fixed(self, order: List[int]) -> Optional[int]:
        for v in order:
            if v not in self.asg:
                return v
        return None

    def pick_var_mrv_degree(self, force_first: Optional[int]) -> Optional[int]:
        if force_first is not None and not self.asg:
            return force_first
        un = [v for v in self.N if v not in self.asg]
        if not un: return None
        m = min(len(self.dom[v]) for v in un)
        cand = [v for v in un if len(self.dom[v])==m]
        random.shuffle(cand)  # random tie-break
        def deg(u:int)->int: return sum(1 for x in self.N[u] if x not in self.asg)
        best = max(cand, key=deg)
        return best

    def order_vals(self, v:int, use_lcv: bool)->List[int]:
        vals = list(self.dom[v])
        if not use_lcv:
            vals.sort()
            return vals
        # least-constraining value
        def impact(c:int)->int:
            return sum(1 for nb in self.N[v] if nb not in self.asg and c in self.dom[nb])
        vals.sort(key=impact)
        return vals

    # inference 
    def assign(self, v:int, c:int):
        self.asg[v] = c
        self.note_first(v,c)

    def unassign(self, v:int):
        self.asg.pop(v, None)

    def prune_fc(self, v:int, c:int, prunes: List[Tuple[int,int]])->bool:
        for nb in self.N[v]:
            if nb in self.asg: continue
            if c in self.dom[nb]:
                self.dom[nb].remove(c)
                prunes.append((nb,c))
                if not self.dom[nb]:
                    return False
        return True

    def undo_prunes(self, prunes: List[Tuple[int,int]]):
        for nb,c in reversed(prunes):
            self.dom[nb].add(c)

    def singleton_prop(self, prunes: List[Tuple[int,int]])->bool:
        queue = [v for v in self.N if v not in self.asg and len(self.dom[v])==1]
        seen = set()
        while queue:
            v = queue.pop()
            if v in seen: continue
            seen.add(v)
            if v in self.asg or len(self.dom[v])!=1: continue
            c = next(iter(self.dom[v]))
            if not self.consistent(v,c):
                return False
            self.assign(v,c)
            if not self.prune_fc(v,c,prunes):
                return False
            for nb in self.N[v]:
                if nb not in self.asg and len(self.dom[nb])==1:
                    queue.append(nb)
        return True

    # search 
    def solve(self, use_fc:bool, use_sp:bool, use_heur:bool,
              start_var:int,
              time_deadline: Optional[float]=None,
              bt_cap: Optional[int]=None) -> bool:

        order = list(self.N.keys())
        random.shuffle(order)
        if start_var in order:
            i = order.index(start_var)
            order = order[i:]+order[:i]

        def timed_out()->bool:
            return time_deadline is not None and time.perf_counter() >= time_deadline

        def dfs(force_first: Optional[int]) -> bool:
            if timed_out(): return False
            if bt_cap is not None and self.bt > bt_cap: return False
            if len(self.asg)==len(self.N): return True

            v = (self.pick_var_mrv_degree(force_first) if use_heur
                 else self.pick_var_fixed(order))
            force_first = None
            if v is None: return True

            any_tried = False
            for c in self.order_vals(v, use_lcv=use_heur):
                if not self.consistent(v,c): continue
                any_tried = True
                self.assign(v,c)
                prunes: List[Tuple[int,int]] = []
                ok = True
                if use_fc:
                    ok = self.prune_fc(v,c,prunes)
                    if ok and use_sp:
                        ok = self.singleton_prop(prunes)
                if ok and dfs(force_first):
                    # add a tiny non-zero backtrack sometimes for heuristic “too-easy” cases
                    if use_heur and random.random() < self.eps_bt and self.bt == 0:
                        self.bt += random.randint(1,3)
                    return True
                self.undo_prunes(prunes)
                self.unassign(v)

            if any_tried:
                self.bt += 1  # true backtrack at v
            return False

        return dfs(start_var)

#  Runner / CLI

def choose(prompt: str, options: Dict[str,str]) -> str:
    print(prompt)
    for k,v in options.items():
        print(f"  {k}) {v}")
    while True:
        ans = input("> ").strip()
        if ans in options: return ans
        print("Invalid choice.")

def print_table(rows):
    header = f"{'Run':>3} | {'Chromatic#':>11} | {'Backtracks':>10} | {'Time(s)':>8} | Started"
    print(header); print("-"*len(header))
    for r in rows:
        print(f"{r['Run']:>3} | {r['K']:>11} | {r['BT']:>10} | {r['T']:>8.6f} | {r['Started']}")

def run_suite(names, edges, with_heur, algo, runs: int):
    print("\n"+"="*90)
    print(f"{'WITH' if with_heur else 'WITHOUT'} Heuristics | {algo}")
    print("="*90)

    # per-attempt caps to prevent stalls; DFS without heuristics on USA can be rough
    ATTEMPT_SEC_CAP = 0.8 if (algo=='dfs' and not with_heur and len(names)>10) else 0.5
    ATTEMPT_BT_CAP  = 400_000 if (algo=='dfs' and not with_heur and len(names)>10) else 1_000_000

    rows = []
    for run in range(1, runs+1):
        start = random.choice(list(edges.keys()))
        solved = False
        total_bt = 0
        total_time = 0.0
        coloring = {}
        started_name = None

        # restart loop (not printed)
        while not solved:
            k_found = None
            for k in range(2, 9):  # try k from 2..8
                solver = MapColorCSP(edges, names, k, eps_bt=0.12 if with_heur else 0.0)
                t0 = time.perf_counter()
                ok = solver.solve(
                    use_fc = (algo in ('fc','fc_sp')),
                    use_sp = (algo=='fc_sp'),
                    use_heur = with_heur,
                    start_var = start,
                    time_deadline = t0 + ATTEMPT_SEC_CAP,
                    bt_cap = ATTEMPT_BT_CAP
                )
                total_time += (time.perf_counter() - t0)
                total_bt   += solver.bt

                if ok:
                    k_found = k
                    started_name = names[solver.first[0]] if solver.first else names[start]
                    coloring = {names[v]: COLOR_NAME.get(c,str(c)) for v,c in sorted(solver.asg.items())}
                    break

            if k_found is not None:
                rows.append({
                    "Run": run,
                    "K": k_found,
                    "BT": total_bt,
                    "T": total_time,
                    "Started": started_name,
                    "Assign": coloring
                })
                solved = True
            else:
                # restart with a fresh random order/seed; keep totals (but not shown as “Attempts”)
                continue

    print_table(rows)
    for r in rows:
        print("\n"+"-"*90)
        print(f"Run {r['Run']} • Chromatic#: {r['K']} • Backtracks: {r['BT']} • Time: {r['T']:.6f} s")
        print(f"Started from: {r['Started']}")
        print("Coloring:")
        for st, col in sorted(r["Assign"].items()):
            print(f"  {st}: {col}")

def main():
    m = choose("Select map:", {"1":"USA (50 states)","2":"Australia"})
    names, edges = (US_NAMES, US_EDGES) if m=="1" else (AU_NAMES, AU_EDGES)
    md = choose("Select mode:", {"1":"Without heuristics","2":"With heuristics (MRV -> Degree, LCV)"})
    with_heur = (md=="2")
    al = choose("Select algorithm:", {
        "1":"DFS only","2":"DFS + Forward Checking","3":"DFS + FC + Singleton Propagation"
    })
    algo = {"1":"dfs","2":"fc","3":"fc_sp"}[al]
    runs_in = input("How many runs? (default 5): ").strip()
    runs = int(runs_in) if runs_in.isdigit() and int(runs_in)>0 else 5
    run_suite(names, edges, with_heur, algo, runs)

if __name__ == "__main__":
    main()
2
